# Controls-testing workpaper

Workpaper: CT-001. Period: October 2026. All evidence is synthetic.

Objective: test independent, timely review and evidence completeness.
Population: 43 records. Sample: 12. Seed: 8421533.
Method: sort unique evidence IDs, then sample without replacement. Input order does not affect selection.
This is a demonstration sample, not a statistical assurance conclusion.

Procedures: inspect preparer, reviewer, date sequence, deadline, evidence reference and SHA-256.
File existence and hashes are checked separately for the full population in evidence_integrity.csv.

Result: 5 sampled records contain evidence exceptions.
Deficiency screens require human judgment. No final significant-deficiency or material-weakness determination is made.

| Evidence | Control | Result | Finding |
| --- | --- | --- | --- |
| E002 | CAPITAL | PASS | None |
| E006 | CAPITAL | PASS | None |
| E007 | LEASE | FAIL | Review past due |
| E009 | RESERVE | PASS | None |
| E010 | CAPITAL | PASS | None |
| E021 | RESERVE | FAIL | Review past due |
| E022 | CAPITAL | FAIL | Reviewer is not independent |
| E024 | VENDOR | PASS | None |
| E031 | LEASE | PASS | None |
| E035 | LEASE | FAIL | Review past due |
| E037 | RESERVE | PASS | None |
| E039 | LEASE | FAIL | Missing evidence artifact or hash; Missing evidence reference |

Preparer: pending. Reviewer: pending. Sign-off date: pending.
Follow-up: findings.csv contains owners, proposed actions and pending review. No remediation is asserted complete.
