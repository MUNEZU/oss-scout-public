# Using OSS Scout

This guide explains how to install OSS Scout, how to ask for what you need, and how to read what comes back. For the short version, see the [README](../README.md).

## Contents

1. [Install](#1-install)
2. [Invoke it](#2-invoke-it)
3. [Pick a mode: Decision or Discovery](#3-pick-a-mode-decision-or-discovery)
4. [Why it sometimes asks one question first](#4-why-it-sometimes-asks-one-question-first)
5. [Prompt patterns that work well](#5-prompt-patterns-that-work-well)
6. [How Discovery ranks projects](#6-how-discovery-ranks-projects)
7. [How Decision reaches a verdict](#7-how-decision-reaches-a-verdict)
8. [Match Score vs Confidence](#8-match-score-vs-confidence)
9. [Evidence, licenses and unknowns](#9-evidence-licenses-and-unknowns)
10. [Worked examples](#10-worked-examples)
11. [Troubleshooting and FAQ](#11-troubleshooting-and-faq)

## 1. Install

Requirements:

- Python 3.10 or later, standard library only;
- Claude Code and/or Codex;
- network access to `api.github.com`, and optionally `api.osv.dev`.

```bash
git clone https://github.com/MUNEZU/oss-scout-public.git
cd oss-scout-public
python3 scripts/install.py --dry-run    # preview
python3 scripts/install.py              # Claude Code + Codex
```

The installer creates two symlinks that point to your checkout:

| Harness | Link |
|---|---|
| Claude Code | `~/.claude/skills/oss-scout` |
| Codex | `~/.agents/skills/oss-scout` |

Useful options:

- `--target claude-code`, or `--target codex`, installs for one harness only.
- `--codex-skills-dir <absolute path>` points Codex at a different skills directory, for example `~/.codex/skills`.
- `--dry-run` prints the plan and changes nothing.

Because they are symlinks, `git pull` in the checkout updates the Skill everywhere. The installer never overwrites an existing file or foreign link. It reports a conflict (exit code 3) instead.

Run it from your main checkout. A temporary git worktree is refused unless you pass `--allow-worktree`, because the link would break when the worktree is removed.

## 2. Invoke it

| Harness | Discovery | Decision |
|---|---|---|
| Claude Code | `/oss-scout discover <goal>` | `/oss-scout decide <goal>` |
| Codex | `$oss-scout discover <goal>` | `$oss-scout decide <goal>` |

You can also just ask in plain language. The Skill picks the mode from your intent:

- "Show me good open-source projects for…", "what OSS is worth trying for…" → **Discovery**
- "I want to build…", "should we build this ourselves?", "is there already an OSS for…?" → **Decision**
- A request that asks for both → Discovery first, then Decision reusing the same evidence.

It does **not** activate for ordinary coding or debugging, for explaining a library you already named, or for choosing between two packages you already picked.

## 3. Pick a mode: Decision or Discovery

| | Discovery | Decision |
|---|---|---|
| Question | "Which OSS fits this best?" | "Should I build this myself?" |
| Typical moment | exploring, learning, shortlisting | before writing code or starting a project |
| Output | 5–10 ranked projects, top picks, what each one does not cover | REUSE / ADAPT / BUILD per capability, overall verdict, remaining gap |
| Forces a verdict? | No | Yes |

If you are unsure, start with Discovery. You can always follow up with "now decide whether I should build it".

## 4. Why it sometimes asks one question first

OSS Scout first restates your **job-to-be-done**, meaning what you are actually trying to achieve. If the context makes the job clear, it states its assumption ("Assuming you want to…") and goes straight to searching.

It asks a question only when two or more plausible jobs would lead to **different kinds of tools**. When it does ask:

- it asks **at most once**, in one message;
- it offers **2–3 short options**;
- it does not ask about your stack or license before the job is clear.

Example: "What Git management and visualization tools do you recommend?" could mean any of:

- a daily Git client;
- a read-only history and branch viewer;
- a way to observe what parallel AI coding agents did across worktrees.

These lead to completely different tools, so one question is cheaper than a wrong shortlist. A request like "observe what my AI coding agents changed across worktrees and branches" is already clear, so it gets no question.

## 5. Prompt patterns that work well

Say the **job**, then any **hard constraints**, then the **license situation** if it matters:

```text
/oss-scout discover <what you want to achieve>, <constraints>, <how it will be used>
```

Good examples:

```text
/oss-scout discover self-hosted tools for visualising OpenTelemetry traces from LLM agents, Docker is fine, internal company use
```

```text
/oss-scout decide a Japanese business-language listening trainer with TTS, ASR and spaced repetition; it may become a paid product
```

```text
What open-source speech recognition projects are best for transcribing Japanese business meetings? It will be part of a paid product.
```

Tips:

- **Name the niche.** Use your domain's own words, including Japanese or Chinese terms. OSS Scout keeps them in its search queries, because that is how small exact-fit projects are found.
- **Say how it will be used**:
  - personal;
  - open-source project;
  - commercial product you distribute;
  - hosted service.

  This sets the license gate. If you don't say, the license target stays `unknown` and is flagged.
- **Say what you don't need.** For example: "I don't need a tool that runs Git for me." This sharpens the framing.
- **Correct it when it misses.** See [section 11](#11-troubleshooting-and-faq).

## 6. How Discovery ranks projects

1. It names the 2–5 use cases you care about. Every project is scored against these.
2. It searches three layers:
   - complete products;
   - specialised or niche matches;
   - general frameworks.
3. It fetches evidence for every GitHub project that may reach the shortlist.
4. It scores each project's **Match Score** and applies **gates**.
5. It keeps 5–10 projects, or fewer if evidence is weak, and never pads the list.

The table you get:

```text
Rank | Project | Match Score | Best for | Why it matches | License | Activity | Confidence
```

It then adds:

- **Top picks to try first**: 1–3 projects that pass every gate, with the reason.
- **What each project does NOT cover**: one line each, so you know the limits up front.
- **Evidence notes**: fetch time, unknowns, and claims verified only by a README.

Gates limit how a project is presented. They never change its score:

| Evidence | Effect |
|---|---|
| Archived | Never a top pick; shown as "reference / learn from" |
| License `blocked-for-target` | Flagged; shown as e.g. "learning only" or "needs a license decision" |
| License `review`, unknown or none | Flagged; Confidence at most `medium` |
| No push for over a year | Marked stale; may still rank if it is finished and an exact fit |

## 7. How Decision reaches a verdict

1. **Frame**: the job and constraints, as in section 4.
2. **Product-first check**: is there already a complete product (OSS, free or commercial) that covers most of the goal? If so, it is reported first, and OSS Scout asks whether to continue at component level. The queries used are listed.
3. **Decompose**: the goal is split into 3–7 capabilities. Each is marked `commodity` (solved elsewhere) or `core` (your product's real value).
4. **Closest-match pass**: before any capability can be marked BUILD, one more targeted search runs in your niche wording. This uses the agent or framework name, domain terms in your language, or the artifact type ("CLI", "React component", "GitHub Action", "MCP server").
5. **Evidence gate**: every REUSE or ADAPT candidate is checked with the evidence script.
6. **Verdict per capability**:
   - **REUSE**: use it as-is.
   - **ADAPT**: wrap, configure, fork or compose it, and say what to change.
   - **BUILD**: nothing fits. The closest-match queries and rejected candidates are listed.
7. **Overall**:
   - **USE EXISTING**: existing tools cover it. Don't build.
   - **ASSEMBLE**: combine existing pieces with some glue.
   - **BUILD THE GAP**: build only the part that is genuinely missing.

The result always ends with **the remaining gap worth building**, and "none" is a valid answer.

## 8. Match Score vs Confidence

These two columns answer different questions:

- **Match Score: how well does this project fit my goal?**

  | Part | Points |
  |---|---|
  | Capability coverage | 0–50 |
  | Domain / use-case fit | 0–30 |
  | Integration fit (stack, deployment, constraints) | 0–20 |

  Stars, forks, downloads and trending position **never** add points. Capabilities claimed only by a README count at most half.
- **Confidence: how solid is the evidence?**
  - `high`: script facts complete, capability verified beyond the README, no unresolved gate.
  - `medium`: script facts complete, but capability seen only in a README or single source, or a license needs review.
  - `low`: a required fact is unknown, or a license conflict is unresolved.

A score is shown exactly (`78`) only when Confidence is `high`. Otherwise it is shown as `~78`. The `~` marks an estimate. It does not lower the rank, which always uses the underlying number.

## 9. Evidence, licenses and unknowns

For every recommended GitHub project, the evidence script records:

- **License** and a **license gate** for your use: `ok`, `review` or `blocked-for-target`.
- **Flags**, such as:
  - `license_network-copyleft` (AGPL);
  - `license_source-available` (for example Elastic-2.0 or BUSL);
  - `license_mixed_or_dual` (for example an `ee/` directory);
  - `license_needs_human_review`;
  - `no_license_detected`.
- **pushed_at** (last push), plus `aging` (over 180 days) or `stale` (over 365 days).
- **archived** state, and whether the repo was renamed or is a fork.
- **fetched_at**: when the facts were fetched, so you know how fresh they are.

You can run it yourself:

```bash
python3 scripts/evidence.py owner/repo https://github.com/owner/other --target commercial
```

When something can't be verified, OSS Scout says so instead of guessing:

| Situation | What you see |
|---|---|
| GitHub rate limit (about 60 requests/hour unauthenticated) | The affected facts are `unknown`; fetching stops; Confidence is `low` |
| Network failure or repo not found | `unknown`, never "no license" or "inactive" |
| Script can't run at all | Results labelled `evidence: unverified` |
| Not on GitHub (commercial product, hosted API, dataset, model weights) | The primary page is cited with its URL and date, and labelled `manual` |

Projects with unknown or unverified evidence are never presented as a clean "use this" top pick. Model weights and datasets often have terms separate from the code license. OSS Scout points this out when it matters.

License flags are not legal advice.

## 10. Worked examples

These are condensed illustrations of real behavior. Your output will include the full tables, queries and evidence notes.

### Discovery: observing AI coding agents

```text
I mainly want to observe what my AI coding agents changed: which worktrees and branches exist, what each one committed, and whether the work has been delivered or merged. I don't really need a tool to run Git operations for me. What open-source tools fit this?
```

What happens:

- **No question:** the job is clear.
- **Frame:** read-only observation of AI-agent development activity, not operating Git.
- **Queries:** use specialised wording, for example "AI coding agent git worktree dashboard" or "agent branch merge status tracker".
- **Ranking:** small specialised tools for multi-agent worktree and branch observation rank above famous generic Git GUIs. Generic GUIs are mentioned only as out of scope.
- **Evidence:** each shortlisted repo shows license, last push and fetch time. Capability claims seen only in READMEs keep Confidence at `medium`, so scores appear as `~N`.

### Decision: should I build an OpenAPI → TypeScript client CLI?

```text
/oss-scout decide a CLI that generates TypeScript API clients from OpenAPI specs
```

What happens:

- **Product-first check:** finds mature generators such as hey-api/openapi-ts, Orval, openapi-typescript and OpenAPI Generator.
- **Capabilities:** spec parsing, typed client generation and CLI packaging are all commodity → **REUSE**.
- **Overall: USE EXISTING.** The remaining gap is "none", unless you need a house-specific template, which would be ADAPT.

### Ambiguous request

```text
What Git management and visualization tools do you recommend?
```

What happens: one short question with 2–3 options (daily Git client / history viewer / observing AI agents' worktrees), and no ranking until you answer.

## 11. Troubleshooting and FAQ

**The skill doesn't trigger.**
Check the link exists: `ls -l ~/.claude/skills/oss-scout` or `ls -l ~/.agents/skills/oss-scout`. Re-run `python3 scripts/install.py --dry-run` to see the plan. Or invoke it explicitly with `/oss-scout` (Claude Code) or `$oss-scout` (Codex).

**I updated the repo but the agent still behaves like an old version.**
The installed Skill is a symlink to your checkout. Run `git pull` in that checkout (not in a temporary worktree), then start a new agent session.

**Lots of `unknown` licenses or a rate-limit note.**
Unauthenticated GitHub access allows about 60 requests per hour. Wait for the reset, or narrow the request so fewer candidates need evidence. Unknown facts are reported honestly and lower Confidence; they are never filled in.

**It asked me a question I think was unnecessary.**
Add the job to your prompt, for example "I want to observe…, not operate…". Clear requests should get no question.

**It missed a tool I know is better.**
Tell it: "You missed X, which fits better because…". OSS Scout then runs a **Miss Analysis**:

- It names one primary cause: a **framing**, **search**, **ranking**, **evidence** or **decision** miss.
- It explains the cause.
- It proposes a regression case for the maintainer to review.
- It re-runs only the affected step.

Nothing is stored automatically.

**A project is flagged `blocked-for-target`. Can I still use it?**
The flag means its license conflicts with the use you described. For example, AGPL conflicts with a hosted service, and GPL conflicts with distributed commercial software. It may still be fine for learning, or with a license decision. Check the actual terms; this is not legal advice.

**Why did a 7-star project rank above a 80,000-star one?**
Because it fits your stated job better. Stars never add points. They only show awareness.

**Does it track trending projects or keep a catalog?**
No. Each run is a point-in-time search. There is no feed, database, telemetry or web UI.
