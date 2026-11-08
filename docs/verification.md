# Verification results

Run date: 2026-11-08. Python: 3.12.14. The requested bundled Python executable was used. All 31 tests pass. No Python dependencies were installed. All tests use `unittest` and the standard library.

## Executed

- Seeded snapshot generation and repeat generation with identical manifest hashes.
- Offline reporting across ten dates, three leases, three borrowers, five vendors and 43 evidence records.
- Unit and integration suite, including hand-computed reserve, haircut, covenant, lease and vendor cases.
- Full GL and journal reconciliation. No failed reconciliations.
- Source tampering, duplicate keys, unsupported inputs, non-finite numbers and unsafe artifact paths.
- Evidence hash failures propagated into covenant evidence status.
- Workbook formula evaluation against 684 Python values, seven input-change checks and formula-error scan.
- Saved workbook inspection and reopened recalculation against all 684 comparisons.
- Visual inspection of all eight worksheets. One renderer preview was refreshed in a fresh workbook session after a display artifact. Saved cell values and formats were correct.
- Author metadata, automatic calculation, absence of external workbook links and plain formatting.

Amounts reconcile within $0.01; periodic rates use an absolute tolerance of 0.000000000001. Saved maximum absolute difference is approximately 0.0000000000582. Formula-error scans found no errors after inputs were restored.

## Written, not executed

`scripts/fetch_sources.py` is the later online retrieval path. The offline shell did not fetch public documents or financial observations. It has not been tested against live host responses. Downloaded documents require content review before the verification register is updated.

## Not verified

Native Microsoft Excel recalculation and printing, the complete current ASC 842 Codification, later accounting amendments, actual broker classifications and regulatory filings, real lease contracts, legal covenant agreements and vendor assertions. No real-world validation is claimed.

Primary-text verification and failed source routes are recorded in [source verification](source_verification.md). Reconciliation details are in `examples/output/`. The Excel verification JSON records the calculation engine and mutation cases.
