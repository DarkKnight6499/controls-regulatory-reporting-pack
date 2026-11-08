# Controls-testing workpaper template

## Identification

Workpaper ID: [ID]. Control ID: [ID]. Period: [start and end]. Process: [name]. Assertion and risk: [specific misstatement or failure]. Control owner: [role]. Frequency: [frequency].

Objective: [what the test establishes]. Criteria: [policy, control description and verified source section if applicable].

## Population and selection

Population source: [file and manifest hash]. Completeness check: [independent reconciliation]. Population count: [N]. Exclusions: [criteria and count]. Sample size: [n]. Method: [seeded random or other]. Seed: [seed]. Selection key: [unique field]. Rationale and assurance limits: [statement].

## Procedure and evidence

1. Reconcile population count and unique identifiers.
2. Inspect preparer, independent reviewer, preparation date, review date and deadline.
3. Locate artifact, compare SHA-256 and reperform the relevant calculation.
4. Record each deviation with its condition, evidence and effect.
5. Assess compensating controls, aggregation and severity before approval.

| Sample ID | Evidence reference and hash | Procedure | Expected | Observed | Result | Exception ID |
| --- | --- | --- | --- | --- | --- | --- |
| [ID] | [path and hash] | [test] | [criterion] | [observation] | [PASS/FAIL/UNAVAILABLE] | [ID] |

## Finding and follow-up

Finding ID: [ID]. Condition: [fact]. Criteria: [requirement]. Cause: [supported cause or not established]. Effect: [specific exposure]. Population implication: [limits]. Severity screen: [screen only]. Final judgment: [approver and rationale]. Compensating controls: [tested evidence].

Owner response: [response]. Remediation: [action]. Due date: [date]. Retest: [procedure, sample and result]. Status: [OPEN or supported closure].

Conclusion: [direct static statement supported by results]. Preparer: [role and date]. Reviewer: [independent role and date]. Approval remains pending until evidence supports sign-off.
