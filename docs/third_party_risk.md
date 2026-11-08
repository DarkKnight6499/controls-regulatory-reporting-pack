# Third-party risk framework

The questionnaire, weights, thresholds and review intervals are fictional internal policy. Scores do not establish vendor safety or regulatory compliance.

## Tier and calendar

Rate criticality, data sensitivity and replacement difficulty from 1 to 5. Inherent risk is their arithmetic mean. Tier 1 begins at 4.0; Tier 2 begins at 2.5; remaining vendors are Tier 3. Review intervals are 90, 180 and 365 calendar days respectively. Next review equals last review plus the tier interval. A review due today is flagged separately from overdue.

## Due diligence

| Question ID | Weight | Question | Example evidence |
| --- | --- | --- | --- |
| security | 3 | Are access, incident response and data-protection controls documented and tested? | Access review and incident exercise |
| continuity | 3 | Can the service recover within the agreed business requirement? | Recovery exercise and documented result |
| financial | 2 | Is financial capacity reviewed against contractual obligations? | Dated financial review |
| compliance | 2 | Are applicable obligations, subcontractors and findings tracked? | Obligation register and remediation log |

Answers: 0 absent, 1 ad hoc, 2 documented, 3 implemented, 4 tested, 5 independently reviewed. Each answer is a supplied assessment. A missing answer or evidence reference earns zero. Unknown questions, duplicates and invalid ratings are rejected.

Questionnaire effectiveness is the sum of `weight * answer / 5`, divided by total weights. Residual risk is `inherent risk * (1 - effectiveness)`. High residual risk begins at 2.5; medium begins at 1.0. The review interval remains driven by inherent tier. No reduction in scheduled oversight is inferred from a strong questionnaire.

Owners investigate high residual risk, incomplete evidence and overdue reviews. The calendar, due-diligence responses and exception log retain vendor IDs for traceability. Seeded evidence files contain fictional responses. They do not establish actual control performance.
