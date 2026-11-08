# Workbook use and rebuild

`controls_reporting_pack.xlsx` contains live reserve and lease formulas. It needs no Python process or network connection to calculate in Excel. Input changes create differences against fixed Python snapshots on Audit.

Inputs: Reserve Ledger A:K; Reserve H for eligible deposits; Lease Inputs B:C value cells. Other cells contain formulas or labels. Periodic rates are monthly rates. Do not change term or add records without rebuilding. Unsupported input populations require model changes first.

The workbook is plain: no cell fills, tab colors or colored fonts. It includes automatic recalculation and cached values. Native Microsoft Excel recalculation was not tested. Artifact-tool recalculation, input-change tests, reopened recalculation and saved-file checks are recorded in `examples/output/excel_verification.json`.

## Rebuild

The Python runtime uses only the standard library. Workbook authoring separately requires Node.js and `@oai/artifact-tool`, supplied by the authoring environment. This dependency is not vendored. The builder resolves it through `.work/node_modules`.

1. Run `python scripts/run_pack.py`.
2. Make `@oai/artifact-tool` available through `.work/node_modules`, using an existing environment installation.
3. Run `node excel/build_workbook.mjs`.
4. Run `python scripts/verify_workbook.py --finalize` to set author metadata, automatic calculation and inspect saved values.
5. Run `node excel/verify_reopen.mjs` to reopen the saved package and recalculate.
6. Review generated previews in `.work/previews/`; delete temporary files after review.

The builder compares 684 formula outputs to Python, changes representative inputs, restores inputs, scans errors and exports one workbook. The saved-file verifier also checks current Python snapshots, author metadata, formatting and external links. Opening the final package in the authoring engine and recalculating was tested separately. This does not establish native Excel behavior.
