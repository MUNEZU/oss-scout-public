# Discovery rules

Read this in Discovery mode before scoring or ranking. It defines the Match Score, the gates that sit beside it, and how to present uncertainty.

## Contents

- Match Score
- Displaying the score
- Gates (separate from the score)
- Ranking and shortlist
- Capability evidence
- Worked example

## Match Score

The Match Score measures **fit to the user's stated goal**. It is a presentation aid, not a quality or popularity score. Score each part from what the project demonstrably does, and write one short reason per part.

| Part | Points | Full points when | Zero when |
|---|---|---|---|
| Capability coverage | 0–50 | It covers every capability or use case named in Frame | It covers none of them |
| Domain / use-case fit | 0–30 | It is built for exactly this domain, agent, framework or language | It is a generic tool that needs heavy adaptation |
| Integration fit | 0–20 | It fits the stated stack, deployment and constraints (self-hosted, offline, language, runtime) | It conflicts with a hard constraint |

Rules:

1. **Stars, forks, downloads and trending position never add points.** You may show them as awareness context only.
2. Score coverage against the capabilities listed in Frame, not against the project's marketing.
3. Capability points claimed only by a README or landing page count at most half, and the row's Confidence is at most `medium`.
4. When two projects tie, prefer the one with stronger evidence, not the more popular one.

## Displaying the score

**Match Score measures fit; Confidence measures evidence quality.** They are separate columns, and one never adds points to the other.

- **Confidence `high`:** show the exact integer, for example `78`.
- **Confidence `medium` or `low`:** show the same estimate with an approximate marker, for example `~78`. Never show a bare integer, because it implies more precision than the evidence supports.
- **Ranking:** always use the underlying estimate. The `~` changes only how the number is shown, never the order.
- Add one line under the table explaining this convention, so the reader does not mistake `~` for a penalty.

## Gates (separate from the score)

The gates come from `scripts/evidence.py` output. They never change the Match Score; they limit how a project may be presented.

| Evidence | Effect |
|---|---|
| `archived: true` | Cannot be a top pick. It may appear only as "reference / learn from", with the flag |
| `license_gate: blocked-for-target` | Shown with the flag; never presented as a clean "use this". The "Best for" column must say e.g. "learning only" or "needs a license decision" |
| `license_gate: review`, `license_unknown`, `no_license_detected` | Flag shown in the License column; Confidence at most `medium` |
| `stale` (no push for over 365 days) | Activity column says stale; may still rank if it is finished and exact |
| Evidence `error` / `partial` | The missing facts are written as `unknown`; Confidence `low` |

## Ranking and shortlist

- Rank by Match Score, highest first. Gates decide only which projects may be top picks.
- Shortlist 5–10 projects; fewer if the evidence is weak. Drop candidates below 40 unless the list would otherwise be empty, and say so.
- Top picks to try first: 1–3 projects that pass the gates, with the reason each one goes first.
- For every shortlisted project, write one line saying what it does **not** cover. This keeps Discovery honest, and gives Decision mode its input when both modes run.

## Capability evidence

Prefer evidence beyond the README: docs, examples, code, issues or release notes. If only the README was read, write `capability evidence: README only` in Evidence notes. Never invent features to fill a capability gap.

## Worked example

Goal: "React components to visualise AI agent traces"; use cases are trace tree, span details, OTel/Langfuse input; constraint is React.

| Project | Coverage | Domain | Integration | Score | Note |
|---|---|---|---|---|---|
| Agent-trace React library (few hundred stars) | 45 | 28 | 18 | 91 | Exact niche match |
| Generic node-graph library (tens of thousands of stars) | 15 | 5 | 18 | 38 | Generic; needs a trace model built on top |

The niche library ranks first. The famous generic library falls below 40 and is mentioned, if at all, as a building block in "What each project does NOT cover".
