# Methodology and limitations

## Regulatory scope

The source register identifies each implemented paragraph. Daily calculations are management monitoring. No assertion is made about mandatory frequency, filing deadlines or complete compliance.

The reserve ledger maps each record to an Exhibit A item. Eligible credits less eligible debits, after the basic-method Item 10 reduction, produce a reserve requirement floored at zero. Deposit shortfall and excess are separate positive amounts. Raw debits means eligible debits before the percentage reduction, not every source receivable. Ages are supplied calendar days. Notes and aging adjustments are not inferred from a general ledger.

Cash debit inputs must be ordinary customer cash accounts with asserted security and collectibility. No margin, omnibus, joint ownership, related-party exception or offset allocation is modeled. Customer qualification is an upstream assumption. Securities borrowing and fails have no same-issue offset allocations. Items 13 through 15 are unsupported. Drafts and overdrawn checks use separate Item 1 categories. Transfer confirmation is a supplied eligibility flag. Unsupported categories fail explicitly.

Net capital starts with book equity, subtracts supplied nonallowable amounts and applies the supported long-position haircuts. Required capital is the greater of the activity floor and aggregate indebtedness divided by the established-broker ratio. Reserve-related indebtedness exclusion uses the smallest of required reserve, eligible deposits and customer payables. No other indebtedness exclusions are claimed. Positions already use market value. Material equity issuer concentrations and unsupported security types fail explicitly. See R1 and R2 in [source verification](source_verification.md).

The synthetic GL deducts an additional $31,000 of receivables in full: unsecured $10,000, doubtful $8,000, affiliated $6,000 and aged fails $7,000. This is a conservative demonstration classification, not a determination of each instrument's regulatory deduction. Detailed receivable rules, fail haircuts, subordination, tax, options, underwriting and alternative-method capital are not implemented. The other GL assets are assumed allowable; actual allowability is not verified.

## Lease conventions

Each period is one month. Payments occur at period end. Inputs provide nonnegative periodic discount rates directly. Classification, useful-life assessment and discount-rate selection are upstream assumptions. Useful life is assumed at least as long as the lease term. There is no ownership transfer or purchase option. Finance ROU amortization uses the lease term. Initial cash flows for prepayments, incentives and direct costs occur at commencement.

The liability starts at discounted unpaid cash flows. Each roll-forward adds periodic accretion and subtracts cash. Finance expense separates accretion and ROU amortization. Operating expense allocates total cost evenly between modifications. Operating ROU amortization is expense less accretion.

A consideration-only modification applies before the effective period's payment. Revised unpaid cash flows and rate determine the liability adjustment. ROU changes by the same amount. Remaining operating cost includes the existing ROU/liability difference; finance amortization resets over remaining periods. The original and revised payment vectors remain separate. Journals balance by event without rounding monthly balances. See A1 and A2 in [source verification](source_verification.md).

## Internal policies

These are fictional policies, not regulatory thresholds.

| Area | Definition |
| --- | --- |
| Net leverage | `max(debt - unrestricted cash, 0) / TTM EBITDA`, maximum 4.0 |
| Interest cover | `TTM EBITDA / TTM interest`, minimum 3.0 |
| Minimum liquidity | Unrestricted cash plus undrawn committed facilities, minimum $500,000 |
| Unavailable ratios | EBITDA at or below zero makes leverage unavailable; zero interest makes cover unavailable. Neither receives PASS. |
| Evidence | Named independent reviewer; review after preparation and by due date; artifact exists and hash matches |
| Variance | Both absolute change at least $100,000 and absolute percentage change at least 10%. A zero prior balance uses the absolute trigger. |
| Sample | Sort unique evidence IDs, sample 12 without replacement using seed 8421533. No statistical assurance claim. |
| Deficiency screen | Impact and likelihood rated 1 to 5. Impact at least 4 and likelihood at least 3 flags potential material weakness. Otherwise impact at least 3 flags potential significant deficiency. Remaining failures flag control deficiency. All require judgment. |

Formal deficiency definitions are verified in C1. The numeric screen is an internal illustration. It does not establish materiality, reasonable possibility, aggregation or compensating-control effectiveness.

## Limits

All financial and operational evidence is synthetic. Balanced synthetic ledgers and matching formulas are internal checks only. Artifacts represent fictional execution statements, not actual approvals of generated reports. Lease and covenant cases do not feed the broker GL. No leases, contracts, security prices, issuer credit quality or vendor claims were independently validated.

The model omits variable/index payments, impairment, term changes, separate-contract modifications, partial termination, classification changes, lessor accounting and disclosures. The original lease ASU is verified; the complete current Codification and later amendments are not. Native Excel calculation and printing are untested. Workbook ranges cover the shipped population. Missing lease input guards are narrower than the Python validation, including unsupported negative ROU cases.

The exception log is regenerated as an open, dated snapshot. Manual resolutions are not retained across reruns. Proposed finding actions are not completed remediation. Hashes establish file consistency, not authenticity or immutable evidence custody.
