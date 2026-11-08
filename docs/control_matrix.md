# Control matrix

All controls and evidence are fictional. The framework uses maker and checker roles, dated artifacts, exception ownership and proposed remediation. No SOX effectiveness opinion is issued.

| ID | Risk and procedure | Frequency | Owner | Evidence and exception |
| --- | --- | --- | --- | --- |
| RESERVE | Recalculate reserve eligibility, aged balances and deposit shortfall | Daily internal monitoring | Treasury | Ledger, reserve detail and deposit reconciliation; log any shortfall |
| CAPITAL | Recalculate supplied nonallowable amounts, position haircuts and capital headroom | Daily internal monitoring | Regulatory Reporting | Trial balance, positions and haircut detail; log negative excess capital |
| VARIANCE | Compare daily reserve and net capital against prior day using both variance triggers | Daily | Reporting Control | Prior/current values and variance table; investigate triggered changes |
| RECON | Tie trial balance, Item 1, deposits, positions, lease balances and journals | Each run | Reporting Control | `reconciliations.csv`; differences above $0.01 produce exceptions |
| COV-* | Compare each borrower with fictional limits and inspect period-specific independent review | Quarterly case | Credit Control | Covenant calculation and matching evidence ID; separate financial breach from evidence failure |
| LEASE | Review contract inputs, modification terms, schedule and balanced journals | Commencement, modification and close | Accounting | Synthetic contracts and schedules; review classification and unsupported terms manually |
| EVIDENCE | Inspect identity, independence, dates, artifact existence and SHA-256 | Each run | Control Owner | Full population results and integrity table; sample workpaper supports findings |
| VENDOR | Tier vendors, score evidence-supported responses and schedule review | Tier calendar | Named vendor owner | Questionnaire, evidence references and review calendar; log overdue, high residual risk or missing evidence |

Exception lifecycle: record condition, assign owner and date, investigate cause, document action, obtain independent review and retest. Generated records start OPEN. The supplied runner does not preserve manual resolution edits.

Deficiency screening uses synthetic impact and likelihood ratings. [Rule 12b-2 definitions](source_verification.md) guide terminology. A material weakness involves a reasonable possibility of a material misstatement not being timely prevented or detected. A significant deficiency is less severe but merits financial-reporting oversight attention. The numeric screen cannot replace those judgments.
