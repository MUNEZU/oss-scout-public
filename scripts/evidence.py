#!/usr/bin/env python3
"""Collect deterministic evidence for OSS candidates and print JSON.

Facts come only from public APIs (GitHub REST, OSV). Nothing is guessed:
missing, rate-limited or unknown values stay explicit in the output.
Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from typing import Any, Callable

GITHUB_API = "https://api.github.com"
OSV_QUERY = "https://api.osv.dev/v1/query"
USER_AGENT = "oss-scout-evidence/0.1"

STALE_DAYS = 365
AGING_DAYS = 180

# SPDX id -> license class. Anything not listed is "other" and needs review.
LICENSE_CLASSES = {
    "MIT": "permissive", "MIT-0": "permissive", "Apache-2.0": "permissive",
    "BSD-2-Clause": "permissive", "BSD-3-Clause": "permissive", "ISC": "permissive",
    "0BSD": "permissive", "Unlicense": "permissive", "Zlib": "permissive",
    "BSL-1.0": "permissive", "CC0-1.0": "permissive", "PostgreSQL": "permissive",
    "Python-2.0": "permissive",
    "LGPL-2.1": "weak-copyleft", "LGPL-3.0": "weak-copyleft",
    "MPL-2.0": "weak-copyleft", "EPL-2.0": "weak-copyleft", "EUPL-1.2": "weak-copyleft",
    "GPL-2.0": "strong-copyleft", "GPL-3.0": "strong-copyleft",
    "AGPL-3.0": "network-copyleft",
    "Elastic-2.0": "source-available", "BUSL-1.1": "source-available",
    "SSPL-1.0": "source-available", "Commons-Clause": "source-available",
}

# Ordered text patterns used only when GitHub cannot assert an SPDX id.
# Each hit is reported as a text match that still needs human review.
LICENSE_TEXT_PATTERNS = [
    (r"Elastic License 2\.0|\bELv2\b", "Elastic-2.0"),
    (r"Business Source License", "BUSL-1.1"),
    (r"Server Side Public License", "SSPL-1.0"),
    (r"Commons Clause", "Commons-Clause"),
    (r"GNU AFFERO GENERAL PUBLIC LICENSE|GNU Affero General Public License", "AGPL-3.0"),
    (r"GNU LESSER GENERAL PUBLIC LICENSE|GNU Lesser General Public License|LGPL ?v?3", "LGPL-3.0"),
    (r"GNU GENERAL PUBLIC LICENSE|GNU General Public License", "GPL-3.0"),
    (r"Mozilla Public License,? (Version |v)?2\.0", "MPL-2.0"),
    (r"Apache License,?\s+Version 2\.0", "Apache-2.0"),
    (r"Permission is hereby granted, free of charge", "MIT"),
]
MIXED_LICENSE_PATTERN = r"\bee/|Portions of this software are licensed|dual[- ]licens|デュアルライセンス"

# Which license classes need attention for each declared use.
TARGET_GATES = {
    "personal": {"review": {"network-copyleft", "source-available", "unknown", "none", "other"}},
    "oss": {"review": {"source-available", "unknown", "none", "other"}},
    "commercial": {
        "blocked": {"strong-copyleft", "network-copyleft", "source-available", "none"},
        "review": {"weak-copyleft", "unknown", "other"},
    },
    "hosted": {
        "blocked": {"network-copyleft", "source-available", "none"},
        "review": {"strong-copyleft", "weak-copyleft", "unknown", "other"},
    },
}

HttpFn = Callable[[str, str, "bytes | None"], "tuple[int, dict[str, str], bytes]"]


def _decode_body(headers: dict[str, str], payload: bytes) -> bytes:
    """Undo gzip transfer compression. A corrupt body raises OSError."""
    if headers.get("content-encoding", "").lower() != "gzip":
        return payload
    try:
        return gzip.decompress(payload)
    except (OSError, EOFError, zlib.error) as exc:
        raise OSError(f"bad gzip body: {exc}") from exc


def http_request(method: str, url: str, body: bytes | None = None, timeout: float = 15.0):
    """Return (status, headers, body). Network and protocol failures raise OSError."""
    # gzip keeps responses small; some proxies truncate large uncompressed bodies.
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json",
               "Accept-Encoding": "gzip"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, _decode_body(resp_headers, resp.read())
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()}
        try:
            payload = _decode_body(resp_headers, exc.read())
        except (OSError, http.client.HTTPException):
            payload = b""
        return exc.code, resp_headers, payload
    except http.client.HTTPException as exc:  # e.g. IncompleteRead on a truncated body
        raise OSError(f"{type(exc).__name__}: {exc}") from exc


def now_iso(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_repo(text: str) -> str | None:
    """Normalize owner/repo, https/git URLs and ssh forms to 'owner/repo'."""
    s = text.strip()
    s = re.sub(r"^git\+", "", s)
    s = re.sub(r"^(https?://)?(www\.)?github\.com[/:]", "", s)
    s = re.sub(r"^git@github\.com:", "", s)
    s = s.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    s = re.sub(r"\.git$", "", s)
    parts = s.split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    pattern = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$"
    if not re.match(pattern, owner) or not re.match(r"^[A-Za-z0-9._-]{1,100}$", repo):
        return None
    return f"{owner}/{repo}"


def classify_license(spdx: str | None) -> str:
    if spdx is None:
        return "none"
    if spdx == "NOASSERTION":
        return "unknown"
    base = re.sub(r"-(only|or-later)$", "", spdx)
    return LICENSE_CLASSES.get(base, "other")


def detect_license_text(text: str) -> dict[str, Any]:
    for pattern, spdx in LICENSE_TEXT_PATTERNS:
        if re.search(pattern, text):
            return {
                "spdx_guess": spdx,
                "class": classify_license(spdx),
                "mixed": bool(re.search(MIXED_LICENSE_PATTERN, text, re.IGNORECASE)),
            }
    return {"spdx_guess": None, "class": "unknown",
            "mixed": bool(re.search(MIXED_LICENSE_PATTERN, text, re.IGNORECASE))}


def license_gate(license_class: str, target: str) -> str:
    rules = TARGET_GATES.get(target)
    if rules is None:
        return "review" if license_class != "permissive" else "ok"
    if license_class in rules.get("blocked", set()):
        return "blocked-for-target"
    if license_class in rules.get("review", set()):
        return "review"
    return "ok"


def _error_from_status(status: int, headers: dict[str, str]) -> dict[str, Any]:
    if status in (403, 429) and (headers.get("x-ratelimit-remaining") == "0" or status == 429):
        return {"kind": "rate_limited", "status": status,
                "reset_epoch": headers.get("x-ratelimit-reset")}
    if status == 404:
        return {"kind": "not_found", "status": status}
    return {"kind": "http_error", "status": status}


def _get_json(http: HttpFn, url: str, sources: list, errors: list, now: datetime, label: str):
    try:
        status, headers, body = http("GET", url, None)
    except OSError as exc:
        sources.append({"url": url, "fetched_at": now_iso(now), "status": None})
        errors.append({"field": label, "kind": "network_error", "detail": str(exc)[:200]})
        return None
    sources.append({"url": url, "fetched_at": now_iso(now), "status": status})
    if status != 200:
        err = _error_from_status(status, headers)
        err["field"] = label
        errors.append(err)
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        errors.append({"field": label, "kind": "bad_response"})
        return None


def repo_evidence(raw: str, target: str, http: HttpFn, now: datetime) -> dict[str, Any]:
    result: dict[str, Any] = {"input": raw, "kind": "github_repo", "status": "error",
                              "facts": {}, "flags": [], "sources": [], "errors": []}
    slug = parse_repo(raw)
    if slug is None:
        result["errors"].append({"field": "input", "kind": "unparseable_repo"})
        return result

    data = _get_json(http, f"{GITHUB_API}/repos/{slug}", result["sources"],
                     result["errors"], now, "repo")
    if data is None:
        return result

    facts = result["facts"]
    facts["canonical_repo"] = data.get("full_name")
    facts["html_url"] = data.get("html_url")
    if facts["canonical_repo"] and facts["canonical_repo"].lower() != slug.lower():
        result["flags"].append("renamed_or_redirected")
    facts["archived"] = bool(data.get("archived"))
    facts["disabled"] = bool(data.get("disabled"))
    facts["is_fork"] = bool(data.get("fork"))
    parent = data.get("parent") or data.get("source")
    facts["fork_parent"] = parent.get("full_name") if isinstance(parent, dict) else None
    facts["pushed_at"] = data.get("pushed_at")
    facts["days_since_push"] = None
    if facts["pushed_at"]:
        try:
            pushed = datetime.strptime(facts["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc)
            facts["days_since_push"] = (now - pushed).days
        except ValueError:
            result["errors"].append({"field": "pushed_at", "kind": "bad_response"})
    # Awareness signal only; never a quality or adoption measure.
    facts["stars_awareness_only"] = data.get("stargazers_count")
    facts["open_issues"] = data.get("open_issues_count")

    lic = data.get("license")
    spdx = lic.get("spdx_id") if isinstance(lic, dict) else None
    license_info: dict[str, Any] = {"spdx": spdx, "source": "github_api",
                                    "class": classify_license(spdx)}
    if spdx == "NOASSERTION" or (spdx is None and isinstance(lic, dict)):
        lic_data = _get_json(http, f"{GITHUB_API}/repos/{facts['canonical_repo'] or slug}/license",
                             result["sources"], result["errors"], now, "license_text")
        text = None
        if lic_data and lic_data.get("encoding") == "base64":
            try:
                text = base64.b64decode(lic_data.get("content", "")).decode("utf-8", "replace")
            except (ValueError, TypeError):
                text = None
        if text:
            detected = detect_license_text(text)
            license_info.update({"source": "license_text_match",
                                 "spdx_guess": detected["spdx_guess"],
                                 "class": detected["class"], "mixed": detected["mixed"]})
            result["flags"].append("license_needs_human_review")
            if detected["mixed"]:
                result["flags"].append("license_mixed_or_dual")
        else:
            license_info["source"] = "unavailable"
            result["flags"].append("license_needs_human_review")
    facts["license"] = license_info
    facts["license_gate"] = license_gate(license_info["class"], target)
    if license_info.get("mixed") and facts["license_gate"] == "ok":
        facts["license_gate"] = "review"

    cls = license_info["class"]
    if cls == "none":
        result["flags"].append("no_license_detected")
    elif cls in ("unknown", "other"):
        result["flags"].append("license_unknown")
    elif cls != "permissive":
        result["flags"].append(f"license_{cls}")
    if facts["archived"]:
        result["flags"].append("archived")
    days = facts["days_since_push"]
    if days is not None and days > STALE_DAYS:
        result["flags"].append("stale")
    elif days is not None and days > AGING_DAYS:
        result["flags"].append("aging")
    if facts["is_fork"]:
        result["flags"].append("fork")

    result["status"] = "partial" if result["errors"] else "ok"
    return result


OSV_ECOSYSTEMS = {
    "npm": "npm", "pypi": "PyPI", "python": "PyPI", "crates.io": "crates.io",
    "cargo": "crates.io", "go": "Go", "maven": "Maven", "nuget": "NuGet",
    "rubygems": "RubyGems", "packagist": "Packagist",
}


def package_evidence(raw: str, http: HttpFn, now: datetime) -> dict[str, Any]:
    """Known advisories for a package via OSV. Other package sources plug in here."""
    result: dict[str, Any] = {"input": raw, "kind": "package", "status": "error",
                              "facts": {}, "flags": [], "sources": [], "errors": []}
    if ":" not in raw:
        result["errors"].append({"field": "input", "kind": "expected_ecosystem:name"})
        return result
    eco_raw, name = raw.split(":", 1)
    ecosystem = OSV_ECOSYSTEMS.get(eco_raw.strip().lower())
    if ecosystem is None or not name.strip():
        result["errors"].append({"field": "input", "kind": "unsupported_ecosystem"})
        return result
    body = json.dumps({"package": {"name": name.strip(), "ecosystem": ecosystem}}).encode()
    try:
        status, headers, payload = http("POST", OSV_QUERY, body)
    except OSError as exc:
        result["sources"].append({"url": OSV_QUERY, "fetched_at": now_iso(now), "status": None})
        result["errors"].append({"field": "osv", "kind": "network_error", "detail": str(exc)[:200]})
        return result
    result["sources"].append({"url": OSV_QUERY, "fetched_at": now_iso(now), "status": status})
    if status != 200:
        err = _error_from_status(status, headers)
        err["field"] = "osv"
        result["errors"].append(err)
        return result
    try:
        vulns = json.loads(payload.decode("utf-8")).get("vulns", [])
    except (ValueError, UnicodeDecodeError, AttributeError):
        result["errors"].append({"field": "osv", "kind": "bad_response"})
        return result
    result["facts"] = {"ecosystem": ecosystem, "name": name.strip(),
                       "osv_advisory_count_all_versions": len(vulns),
                       "osv_ids": sorted(v.get("id", "") for v in vulns)[:50]}
    if vulns:
        result["flags"].append("has_osv_advisories")
    result["status"] = "ok"
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evidence.py",
        description="Fetch deterministic evidence (license, recency, archived state, "
                    "sources) for OSS candidates and print JSON. No values are guessed.")
    p.add_argument("repos", nargs="*", help="GitHub repos as owner/repo or URL")
    p.add_argument("--package", action="append", default=[], metavar="ECOSYSTEM:NAME",
                   help="also query OSV advisories, e.g. npm:express or pypi:requests")
    p.add_argument("--target", default="unknown",
                   choices=["personal", "oss", "commercial", "hosted", "unknown"],
                   help="intended use, decides license_gate (default: unknown)")
    p.add_argument("--timeout", type=float, default=15.0, help="per-request timeout seconds")
    return p


def run(argv: list[str], http: HttpFn | None = None, now: datetime | None = None) -> dict:
    args = build_parser().parse_args(argv)
    if not args.repos and not args.package:
        build_parser().error("give at least one repo or --package")
    now = now or datetime.now(timezone.utc)
    if http is None:
        def http(method, url, body):  # noqa: E306
            try:
                return http_request(method, url, body, timeout=args.timeout)
            except OSError:  # one retry for transient network/proxy failures
                return http_request(method, url, body, timeout=args.timeout)
    items = [repo_evidence(r, args.target, http, now) for r in args.repos]
    items += [package_evidence(p, http, now) for p in args.package]
    return {
        "schema": "oss-scout/evidence/1",
        "generated_at": now_iso(now),
        "target": args.target,
        "summary": {s: sum(1 for i in items if i["status"] == s)
                    for s in ("ok", "partial", "error")},
        "items": items,
    }


def main(argv: list[str] | None = None) -> int:
    out = run(sys.argv[1:] if argv is None else argv)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
