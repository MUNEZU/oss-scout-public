# Miss analysis

Read this when the user supplies a clearly better candidate that was missed, corrects the intended job, or shows that a recommendation or verdict was wrong. Diagnose first; don't just re-score the new candidate.

## Contents

- The five classes
- How to choose the primary class
- Output
- What this is not

## The five classes

There are exactly five root classes. Do not invent others.

| Class | Meaning |
|---|---|
| **framing miss** | The wrong job or use case was inferred, so the search targeted the wrong kind of tool |
| **search miss** | The framing was right, but the queries or search layers did not reach the candidate |
| **ranking miss** | The candidate was found, but it was scored or presented too low |
| **evidence miss** | Available evidence was missing or handled incorrectly, and that changed the recommendation |
| **decision miss** | Search and evidence were adequate, but the REUSE / ADAPT / BUILD verdict, or the overall decision, was wrong |

## How to choose the primary class

Check the classes in this order, and stop at the first that applies. An earlier failure usually causes the later ones.

1. Would the right job description have led to a different candidate class? → **framing miss**.
2. Did any query or search layer from the run plausibly reach the candidate? If not → **search miss**.
3. Was the candidate in the pool but ranked below weaker ones? → **ranking miss**.
4. Was a fact (license, activity, archived state, capability) missing or misread in a way that changed its placement? → **evidence miss**.
5. Otherwise, if the verdict itself was wrong → **decision miss**.

Name one primary class. You may mention a contributing secondary cause in one clause.

## Output

```text
Miss analysis
Primary class: <framing | search | ranking | evidence | decision> miss
Cause: <one or two sentences, specific to this run>
Regression: <add or update which eval case, with the prompt idea and the expectation that would have caught it>
Corrected result: <re-run only the affected step; then give the corrected ranking or verdict>
```

## What this is not

- Not a database, telemetry or automatic write-back. Nothing is stored by the Skill.
- The regression line is a proposal for whoever maintains `evals/evals.json`.
- Not a reason to add special-case rules for one product name. Fix the general step that failed.
