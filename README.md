# Controls and Regulatory Reporting Pack

Offline Python calculations and a live Excel workbook for synthetic financial reporting and control testing. All ledgers, contracts, evidence and vendor responses are fictional. Seed: `8421533`. Amounts are USD.

| Component | Implementation | Main output |
| --- | --- | --- |
| Customer reserve | Restricted SEC Rule 15c3-3 Exhibit A, eligibility exclusions, aging and debit reduction | `reserve_daily.csv`, `reserve_detail.csv` |
| Net capital | Selected Rule 15c3-1 basic-method adjustments, security haircuts and capital headroom | `capital_daily.csv`, `haircuts.csv` |
| Covenants | Net leverage, interest cover, minimum liquidity and review evidence | `covenant_compliance.csv` |
| Leases | Operating and finance schedules, modification remeasurement, ROU roll-forward and journals | `lease_schedule.csv`, `lease_journals.csv` |
| Controls testing | Seeded sample, evidence checks, deficiency screens and findings | `controls_workpaper.md`, `findings.csv` |
| Third-party risk | Tiering, weighted questionnaire, residual risk and review calendar | `vendor_reviews.csv` |

## Run offline

Python 3.10 or later. The Python library and tests use only the standard library. No installation or network access is required.

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python scripts/run_pack.py
$env:PYTHONPATH = "python"
python -m unittest discover -s python/tests -v
python scripts/verify_workbook.py
```

Open [the workbook](excel/controls_reporting_pack.xlsx). The Reserve tab calculates from its raw ledger. Three lease tabs calculate from editable contract inputs. Audit compares 684 live values against Python snapshots. Recalculation is automatic; input edits expose differences until Python and the workbook are refreshed.

Regenerate the same input snapshot with `python scripts/generate_synthetic.py`. This overwrites synthetic inputs. Assumptions live in the configuration blocks in `python/controls_pack/config.py` and `synthetic.py`. Workbook rebuilding requires a separate JavaScript authoring dependency; see [Excel instructions](excel/README.md).

## Shipped example

Ten business days, October 19 to 30, 2026; three leases and 54 monthly periods; three borrowers; five vendors. The control population contains 43 records. A 12-record sample contains five evidence exceptions. The exception log contains 26 records, including the planted reserve shortfall and capital breach. These are separate fictional cases, not consolidated entities.

Generated tables live in `examples/output/`. Snapshot and run manifests record SHA-256 hashes. Reconciliations cover the trial balance, reserve Item 1, reserve deposits, firm securities, lease ending balances and journal balance. They test internal consistency, not real-world validity.

## Scope and limitations

The reserve model supports selected items and ordinary cash accounts. It is not a complete broker-dealer filing engine. Net capital uses supplied nonallowable classifications and selected deductions. Lease classification is supplied; modifications only change consideration.

Rule text was checked against eCFR and FASB primary documents on November 8, 2026. Later ASC 842 amendments were not exhaustively verified. Native Microsoft Excel recalculation was not tested. Control ratings, covenant limits, sample size and vendor policies are fictional. There is no real-world validation.

See [methodology and limitations](docs/methodology.md), [source verification](docs/source_verification.md), [data dictionary](docs/data_dictionary.md), [control matrix](docs/control_matrix.md) and [workpaper template](docs/workpaper_template.md).

Optional `python scripts/fetch_sources.py` downloads primary documents into `data/public/` with a manifest. It is separate from the offline library and was not run in the offline shell. It fetches rule documents, not financial observations.
