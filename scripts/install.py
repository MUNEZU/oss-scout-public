#!/usr/bin/env python3
"""Install this repository as the `oss-scout` Skill by symlinking it into
user-scope skill directories. Never overwrites anything that is already there.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SKILL_NAME = "oss-scout"
REPO_ROOT = Path(__file__).resolve().parents[1]

# User-scope skill directories, relative to the home directory.
TARGETS = {
    "claude-code": Path(".claude") / "skills",
    "codex": Path(".agents") / "skills",
}

EXIT_OK = 0
EXIT_CONFLICT = 3
EXIT_BAD_SOURCE = 2


def check_source(source: Path, allow_worktree: bool) -> str | None:
    """Return an error message if `source` is not a usable, durable Skill root."""
    if not (source / "SKILL.md").is_file():
        return f"{source} has no SKILL.md"
    if (source / ".git").is_file() and not allow_worktree:
        # A linked git worktree is usually temporary; a symlink to it would break later.
        return (f"{source} is a linked git worktree; install from the main checkout "
                "or pass --allow-worktree")
    return None


def plan(home: Path, source: Path, targets: list[str], roots: dict[str, Path]) -> list[dict]:
    """Decide, without writing, what happens at each destination."""
    source = source.resolve()
    steps = []
    for target in targets:
        dest = home / roots[target] / SKILL_NAME if not roots[target].is_absolute() \
            else roots[target] / SKILL_NAME
        step = {"target": target, "path": str(dest), "source": str(source)}
        if dest.is_symlink():
            link = os.readlink(dest)
            resolved = (dest.parent / link).resolve() if dest.exists() else None
            step["existing_link"] = link
            if resolved == source:
                step["action"] = "already_installed"
            else:
                step["action"] = "conflict"
                step["reason"] = ("broken symlink" if resolved is None
                                  else f"symlink to a different location: {resolved}")
        elif dest.exists():
            step["action"] = "conflict"
            step["reason"] = "a real file or directory already exists"
        else:
            step["action"] = "create"
        steps.append(step)
    return steps


def apply(steps: list[dict]) -> None:
    for step in steps:
        if step["action"] != "create":
            continue
        dest = Path(step["path"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(step["source"], dest, target_is_directory=True)
        step["action"] = "created"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install.py",
        description=f"Symlink this repository as the '{SKILL_NAME}' Skill into user-scope "
                    "skill directories (Claude Code: ~/.claude/skills, Codex: ~/.agents/skills). "
                    "Existing files, directories and foreign symlinks are never overwritten.")
    p.add_argument("--target", choices=["all", *TARGETS], default="all",
                   help="which harness to install for (default: all)")
    p.add_argument("--source", type=Path, default=REPO_ROOT,
                   help="Skill root to link to (default: this repository)")
    p.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    p.add_argument("--codex-skills-dir", type=Path,
                   help="override the Codex skills directory (absolute path)")
    p.add_argument("--allow-worktree", action="store_true",
                   help="allow linking to a linked git worktree (usually temporary)")
    p.add_argument("--dry-run", action="store_true", help="show the plan and change nothing")
    return p


def run(argv: list[str]) -> tuple[int, dict]:
    args = build_parser().parse_args(argv)
    source = args.source.resolve()
    roots = dict(TARGETS)
    if args.codex_skills_dir:
        roots["codex"] = args.codex_skills_dir.expanduser().resolve()
    error = check_source(source, args.allow_worktree)
    if error:
        return EXIT_BAD_SOURCE, {"ok": False, "error": error, "steps": []}
    targets = list(TARGETS) if args.target == "all" else [args.target]
    steps = plan(args.home, source, targets, roots)
    if not args.dry_run:
        apply(steps)
    conflicts = [s for s in steps if s["action"] == "conflict"]
    return (EXIT_CONFLICT if conflicts else EXIT_OK), {
        "ok": not conflicts, "dry_run": args.dry_run, "steps": steps}


def main(argv: list[str] | None = None) -> int:
    code, out = run(sys.argv[1:] if argv is None else argv)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
