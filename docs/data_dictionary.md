# Data dictionary

All source tables are under `data/synthetic/`. No public observations are present. Dates use ISO `YYYY-MM-DD`; amounts are USD; booleans are `True` or `False`. CSV loading enforces exact field names. Domain functions validate supported values and unique keys.

| File | Key | Fields and interpretation |
| --- | --- | --- |
| `reserve_ledger.csv` | `record_id` | `date`, `category`, `amount`, `age_days`, `market_value`, `secured`, `collectible`, `affiliate`, `account_type`, `transfer_confirmed`. Amounts and market values are nonnegative magnitudes. |
| `positions.csv` | `position_id` | `date`, `issuer`, `asset_class`, `market_value`, `side`. Supported classes: `listed_equity`, `qualifying_money_fund`; supported side: `long`. Issuer aggregates lots for concentration checks. |
| `trial_balance.csv` | `date`, `account` | `classification`, `balance`. Debit balances positive; credit balances negative. Classes: `asset`, `nonallowable`, `liability`, `equity`. Sum must reconcile to zero. |
| `daily_inputs.csv` | `date` | `eligible_deposit`. Eligibility is supplied, not independently verified. |
| `covenants.csv` | `borrower_id`, `date` | `debt`, `unrestricted_cash`, `undrawn_committed`, `ttm_ebitda`, `ttm_interest`. No EBITDA add-backs or legal agreement interpretation. |
| `control_population.csv` | `evidence_id` | `date`, `control_id`, `preparer`, `reviewer`, `prepared_on`, `reviewed_on`, `due_on`, `artifact_ref`, `artifact_sha256`, `impact`, `likelihood`. References are relative to project root. |
| `vendors.csv` | `vendor_id` | `service`, `owner`, `criticality`, `data_sensitivity`, `substitutability`, `last_review`. Higher substitutability rating means harder to replace. |
| `questionnaire.csv` | `vendor_id`, `question_id` | `answer`, `evidence_ref`. Integer answers 0 to 5. Blank answer or reference earns zero effectiveness. |
| `leases.json` | `lease_id` | `kind`, `payments`, `periodic_rate`, `prepaid`, `incentive`, `initial_direct_cost`, `modification`. Payment arrays are chronological monthly amounts. |

The modification object contains `effective_period`, `remaining_payments`, `periodic_rate` and `change_type`. Only `consideration_only` is supported. The revised vector must have exactly the number of periods remaining in the original term.

## Reserve categories

| Item | Categories |
| --- | --- |
| 1 | `free_credit`, `customer_draft`, `overdrawn_check` |
| 2 to 5 | `borrowed_money`, `securities_loaned`, `failed_receive`, `principal_sale` |
| 6 to 9 | `distribution`, `short_count`, `suspense`, `transfer` |
| 10 to 12 | `customer_debit`, `securities_borrowed`, `failed_deliver` |

For items 6 to 9, eligible values use `market_value`. For securities loans, `amount` means cash collateral payable; market value may add a credit enhancement. Fail values use contract amount with the implemented age adjustment. Category labels require upstream classification.

## Output conventions

`reserve_daily.csv` and `capital_daily.csv` contain one record per date. `lease_schedule.csv` contains one record per lease and period. `lease_journals.csv` identifies balanced events through `journal_id`. `covenant_compliance.csv` separates financial status, evidence status and overall status. Unavailable numeric values are empty CSV fields, not zero.

`daily_exception_log.csv` uses a stable ID built from date, control and entity. It includes severity, observed condition, expected condition, owner, due date, status, evidence reference and resolution. The due-date policy is five calendar days. These are proposed internal actions.

`manifest.json` hashes source and evidence files. `run_manifest.json` hashes report files. `workbook_inputs.json` holds typed source records and Python comparisons for the workbook builder. `excel_verification.json` records formula recalculation, mutations and saved-file checks separately from native Excel testing.
