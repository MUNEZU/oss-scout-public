# Evidence rules

Read this before writing any REUSE or ADAPT verdict or a Discovery ranking. It defines which facts are required, where they come from, and what must never be inferred.

## Contents

- Required evidence per candidate
- License handling
- Recency and maintenance
- What must not be inferred
- Confidence
- Script output reference

## Required evidence per candidate

Every candidate given REUSE or ADAPT, and every project in a Discovery shortlist, needs these fields from `scripts/evidence.py`. They must not come from memory, search snippets, or a README.

| Field | Source | If missing |
|---|---|---|
| Canonical repo | `facts.canonical_repo` (follows renames) | Say "not verified"; the candidate cannot be REUSE |
| License | `facts.license` + `facts.license_gate` | Write `license: unknown`; never fill in from memory |
| Last push | `facts.pushed_at`, `facts.days_since_push` | Write `recency: unknown` |
| Archived | `facts.archived` | Write `archived: unknown` |
| Sources | `sources[].url` + `sources[].fetched_at` | Cite the fetch time next to the facts |

Candidates that are not on GitHub (a commercial product, a hosted API, a dataset, a package without a repo) cannot pass through the script. Cite the primary page you read, with its URL and date, and label the evidence `manual`.

For packages, `--package ECOSYSTEM:NAME` adds known OSV advisories. Treat the count as "has known advisories in some version". It is not a verdict on the version you would install.

## License handling

The script reports a license class and a `license_gate` for the declared `--target`:

| Class | Examples | Meaning for the verdict |
|---|---|---|
| permissive | MIT, Apache-2.0, BSD, ISC | Usually fine |
| weak-copyleft | LGPL, MPL, EPL | Fine to link; modifying it has obligations |
| strong-copyleft | GPL | Distributing a combined work triggers copyleft |
| network-copyleft | AGPL | Offering it as a network service triggers copyleft |
| source-available | Elastic-2.0, BUSL, SSPL | Not open source; usage limits apply |
| unknown / other / none | NOASSERTION, custom text, no license file | No usage rights can be assumed |

Rules:

1. Show every flag the script reports (for example `license_network-copyleft` or `license_mixed_or_dual`) next to the candidate in the output.
2. `license_gate: blocked-for-target` means the candidate cannot be REUSE for that target. At most it can be ADAPT with an explicit license decision for the user, or an alternative.
3. `license_gate: review` means you may recommend the candidate, but the flag goes into the verdict line.
4. `source: license_text_match` is a pattern match on the license file, not a legal determination. Keep `license_needs_human_review` visible.
5. A repo that mixes licenses (for example an `ee/` directory) or offers dual licensing needs a sentence on which part the user would use.
6. Model weights, voice libraries, and datasets often have terms separate from the code license. Say so when they matter, and cite the page that states the terms.
7. This is not legal advice; say so once when a flag affects the decision.

## Recency and maintenance

- `days_since_push > 365` → `stale`; `> 180` → `aging`. Stale is not automatically disqualifying (finished libraries exist), but REUSE of a stale repo needs a reason.
- `archived: true` → never REUSE. ADAPT means forking, so say that.
- `fork` → check whether `fork_parent` is the better candidate.
- `stars_awareness_only` shows awareness. It is not adoption or quality, and must never be a ranking key on its own.

## What must not be inferred

- A license, push date, or archived state the script did not return.
- A capability that is described only in a README or marketing page. Confirm it in docs, examples, code, issues, or release notes, or mark it `capability: unverified`.
- "No suitable tool exists". That claim requires the closest-match pass from `SKILL.md`.
- That an error means a negative. `rate_limited`, `network_error`, and `not_found` mean "unknown". Report them as unknown.

## Confidence

Assign confidence per verdict from evidence coverage, not from how sure the model feels:

- **high**: script facts complete, capability verified outside the README, no unresolved gate.
- **medium**: script facts complete, but the capability is verified only by README or a single source, or the gate is `review`.
- **low**: any required field unknown, `status` partial/error, or `blocked-for-target` unresolved.

## Script output reference

```text
python3 scripts/evidence.py OWNER/REPO [URL ...] [--package ECOSYSTEM:NAME] [--target personal|oss|commercial|hosted|unknown]
```

Output schema `oss-scout/evidence/1`: `summary` counts `ok/partial/error`. Each item has `status`, `facts`, `flags`, `sources`, and `errors`. Errors have a `kind`: `rate_limited` (with `reset_epoch`), `not_found`, `network_error`, `http_error`, `bad_response`, or `unparseable_repo`. The script retries a failed request once, then reports the error. It never substitutes a value. Unauthenticated GitHub API access allows about 60 requests per hour, so batch candidates into one call.
