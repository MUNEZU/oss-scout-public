---
name: oss-scout
description: Open-source scouting in two modes. Decision mode — before building a tool, app, feature or system, finds what already exists and decides REUSE / ADAPT / BUILD per capability with verified evidence (fetched license, last push, archived state), then states the gap worth building. Discovery mode — returns a ranked shortlist of the OSS projects most relevant to a goal or domain, ranked by goal fit (never by stars) with license and activity evidence. Use when the user writes "/oss-scout decide …" or "/oss-scout discover …", or says "I want to build X", "should we build this ourselves?", "is there already an OSS for X?", "show me good open-source projects for X", "what OSS is worth trying or learning from for X". Companion to the search-first workflow. Do not use for ordinary coding or debugging, explaining a known library, choosing between two packages already named, or daily trending/star-history monitoring.
---

# oss-scout

Two modes share one evidence discipline:

- **Decision mode** answers "should I build this myself?": what exists, what can be reused or adapted, and what remains worth building. "An existing solution is enough, don't build" is a valid and good outcome.
- **Discovery mode** answers "which OSS projects are best for this purpose?": a bounded, ranked shortlist to inspect, learn from, try or adopt. It never forces a BUILD verdict.

## Choose the mode

| Request | Mode |
|---|---|
| `/oss-scout decide <goal>`, or build intent: "I want to build…", "should we build…", "do we need to implement…" | Decision |
| `/oss-scout discover <goal>`, or browse intent: "show me good OSS for…", "most relevant open-source projects for…", "projects worth trying / learning from…" | Discovery |
| Both intents in one request | Discovery first, then Decision using the Discovery evidence |

Do not ask the user to pick a mode when the intent is clear. Ask only when the request fits neither row.

## Relationship to search-first

This Skill extends the search-first workflow (need analysis → parallel search → evaluate → adopt/extend/build) instead of replacing it. If a search-first Skill is installed, follow its need analysis and search channels and add the steps marked **[scout]**. If it is not installed, the short versions below are enough.

## Shared steps

### Frame

1. **Job-to-be-done first.** In one or two lines, restate what the user is actually trying to accomplish, before any technical constraint. When the context makes the job reasonably clear, infer it and state the assumption briefly ("Assuming you want to …").
2. **Ask only on a material fork.** If two or more plausible jobs would lead to a different class of candidates or a different ranking, ask **at most once**, in one message, offering 2–3 concise options. If the request is already clear, do not ask. Never ask only because the stack or license is unknown.
3. **Constraints second.** Then collect only the facts that change the result. Anything unknown stays `unknown`; say so once.
   - stack and language, if fixed;
   - license target: `personal`, `oss`, `commercial` (closed distribution) or `hosted` (offered as a network service);
   - hard constraints, such as self-hosted, offline, or Japanese-language support.
4. **Carry the job into every query.** Every search query includes the inferred or confirmed job/use-case wording. For niche domains, keep the user's language and domain terms (for example the Japanese terms) instead of normalising everything to generic English.

### Evidence [scout]

Run the evidence script once, with every GitHub candidate you will recommend, rank or mark REUSE/ADAPT:

```text
python3 scripts/evidence.py owner/repo https://github.com/owner/repo2 --target <license target>
```

Add `--package ecosystem:name` for packages to see known OSV advisories. Read [evidence rules](references/evidence-rules.md) before writing verdicts or rankings, so you know which facts are required, how licenses are handled, and what must not be inferred.

- Copy license, last push, archived state and flags from the script output. Never take them from memory or snippets.
- Script `error` or `partial` → mark the fact `unknown` and lower confidence. Do not retry repeatedly and do not guess.
- If the script cannot run (no Python, no network), say so, and label every affected result `evidence: unverified`.

## Decision mode

1. **Frame** (shared step).
2. **Product-first check [scout].** Before looking at components, search for complete products that already cover most of the goal: OSS applications, and free or commercial products. Label each one `OSS`, `free` or `commercial`. If one covers most of the goal, report it first and ask whether to continue at component level, unless the user already said they must build. Record the queries used; a check without listed queries does not count as done.
3. **Decompose and broad search.** Split the goal into 3–7 capabilities, each marked `commodity` or `core`. Search frameworks and components, libraries and packages, and existing tool servers or skills. Budget: at most 3 queries and 5 shortlisted candidates per capability.
4. **Closest-match pass [scout].** Before any capability gets BUILD, run one more targeted search per capability that still has no fit, using the user's exact niche wording: the agent or framework name, the domain term in the user's language (for Japanese domains, the Japanese terms too), or the artifact type ("React component", "CLI", "GitHub Action", "MCP server", "dataset", "API"). BUILD is allowed only after this pass, and the output lists its queries. Popular searches failing is not a reason to BUILD.
5. **Evidence gate [scout]** (shared step) for every REUSE/ADAPT candidate. `license_gate: blocked-for-target` → not REUSE.
6. **Decide.** Each capability gets **REUSE** (use as-is), **ADAPT** (wrap, configure, fork or compose) or **BUILD**. The overall decision is **USE EXISTING**, **ASSEMBLE** or **BUILD THE GAP**.

Stop conditions:

- A capability gets a REUSE candidate that passes the evidence gate → stop searching that capability.
- A complete product covers most of the goal → stop after step 2 and report, unless the user asks to continue.
- Query budget used up and closest-match pass done → stop; report "not found, low confidence". Never invent a candidate.
- Evidence API rate-limited → stop fetching; report which facts are unknown.

Output contract:

```text
Goal / constraints / license target
Product-first check: <products found + label + coverage> | queries: ...
Capabilities:
  C1 <name> [commodity|core] — REUSE <repo> | license <spdx> (<gate>, flags) | pushed <date> | archived <bool> | fetched <time> | capability verified by <source> | confidence <h/m/l>
  C2 <name> — ADAPT <repo> (what to wrap/change) | <same evidence fields>
  C3 <name> — BUILD | closest-match queries: ... | rejected: <candidate — reason>
Overall: USE EXISTING | ASSEMBLE | BUILD THE GAP
Remaining gap worth building: <one paragraph; "none" is allowed>
Unknowns / missing evidence: ...
```

## Discovery mode

1. **Frame** (shared step). Name the 2–5 capabilities or use cases the user cares about; the ranking is scored against these.
2. **Search three layers [scout].** Complete products and applications, specialised or niche matches (use the closest-match wording from Decision step 4), and general frameworks or libraries. Budget: about 10 queries and at most 20 candidates in the pool.
3. **Evidence [scout]** (shared step) for every GitHub candidate that may reach the shortlist.
4. **Score and gate.** Read [discovery rules](references/discovery-rules.md) and give each candidate a Match Score (capability coverage 0–50, domain fit 0–30, integration fit 0–20). Stars never add points. Gates are applied separately: archived projects cannot be top picks, and a `blocked-for-target` or unknown license is flagged and never presented as a clean "use this".
5. **Shortlist.** Keep 5–10 projects, fewer if evidence is weak. A low-star exact niche match may outrank a famous generic framework.

Stop when the budget is used up or the pool has no further candidates scoring at least 40. Never pad the shortlist.

Output contract:

```text
Goal / use cases / license target
Rank | Project | Match Score | Best for | Why it matches | License | Activity | Confidence
Top picks to try first: <1–3, with the reason>
What each project does NOT cover: <one line each>
Evidence notes: <fetch time, unknowns, capability claims verified only by README>
```

Match Score display: show an exact integer only when Confidence is `high`, otherwise `~N`. Match Score measures fit, Confidence measures evidence; see [discovery rules](references/discovery-rules.md).

## When a recommendation is shown to be wrong

If the user supplies a clearly better candidate that was missed, corrects the intended job, or shows a verdict to be wrong, read [miss analysis](references/miss-analysis.md). Diagnose the primary miss class before re-ranking or re-deciding.

## Not in scope

Scheduled or daily trending feeds, star-history tracking, persistent catalogs, and package-wide security scanning. License flags are not legal advice.
