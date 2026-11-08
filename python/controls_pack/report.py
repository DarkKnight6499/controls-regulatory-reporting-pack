"""Offline report runner with source integrity checks and reproducible outputs."""
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .common import sha256, unique, write_csv, write_json
from .config import (AS_OF, DATA_DIR, MONEY_TOLERANCE, OUTPUT_DIR, ROOT, SAMPLE_SIZE, SEED)
from .controls import Evidence, deficiency, exception_record, select_sample, test_evidence, variance
from .covenants import CovenantInput, evaluate_covenants
from .io import load_records
from .leases import Lease, Modification, journals, schedule
from .regulatory import Position, ReserveRow, net_capital, reserve
from .synthetic import DailyInput, TrialBalanceRow
from .vendors import Response, Vendor, vendor_risk

# Configuration
MANIFEST_NAME = "manifest.json"
LEASES_NAME = "leases.json"
MANIFEST_FILES = "files"
MANIFEST_EVIDENCE = "evidence_files"
PATH_FIELD = "path"
HASH_FIELD = "sha256"
MODIFICATION_FIELD = "modification"
PAYMENTS_FIELD = "payments"
REMAINING_PAYMENTS_FIELD = "remaining_payments"
RESERVE_GL_ACCOUNTS = {"Customer free credit", "Customer drafts"}
RESERVE_SOURCE_CATEGORIES = {"free_credit", "customer_draft", "overdrawn_check"}
RESERVE_ACCOUNT = "Reserve deposit"
SECURITIES_ACCOUNT = "Firm securities"
RECON_FIELDS = ["date", "check", "difference", "status"]
VARIANCE_FIELDS = ["date", "metric", "current", "previous", "amount_change", "percent_change", "exception"]
FINDING_FIELDS = ["finding_id", "evidence_id", "control_id", "condition", "criteria", "cause",
                  "effect", "deficiency_screen", "owner", "action", "due_on", "review_status"]
EXCEPTION_FIELDS = list(exception_record(AS_OF, "", "", "", "", "", "", "").__dict__)
NETWORK_MODULES = {"requests", "urllib", "http", "socket", "httpx", "aiohttp"}
STATUS_FIELD = "status"
EQUITY_CLASS = "equity"
ASSET_CLASS = "asset"
LIABILITY_CLASS = "liability"
NONALLOWABLE_CLASS = "nonallowable"
VALID_GL_CLASSES = {EQUITY_CLASS, ASSET_CLASS, LIABILITY_CLASS, NONALLOWABLE_CLASS}
OFFICE_ACCOUNT = "Office payable"
EXPECTED_SOURCE_FILES = {"reserve_ledger.csv", "positions.csv", "trial_balance.csv", "daily_inputs.csv",
                         "control_population.csv", "covenants.csv", "vendors.csv", "questionnaire.csv", "leases.json"}
SYNTHETIC_FIELD = "synthetic"
FINDING_DUE = "2026-11-06"
DATE_KEYS = ["date"]
TRIAL_BALANCE_KEYS = ["date", "account"]
EVIDENCE_KEYS = ["evidence_id"]
COVENANT_KEYS = ["borrower_id", "date"]
VENDOR_KEYS = ["vendor_id"]
RESPONSE_KEYS = ["vendor_id", "question_id"]
LEASE_KEYS = ["lease_id"]


@dataclass(frozen=True)
class RunSummary:
    synthetic: bool
    seed: int
    as_of: str
    reserve_days: int
    lease_periods: int
    lease_count: int
    population_size: int
    sample_size: int
    sample_failures: int
    exceptions: int
    failed_reconciliations: int


def verify_manifest(directory):
    manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    if manifest.get(SYNTHETIC_FIELD) is not True:
        raise ValueError("Only explicitly synthetic snapshots are supported")
    if {item[PATH_FIELD] for item in manifest[MANIFEST_FILES]} != EXPECTED_SOURCE_FILES:
        raise ValueError("Manifest must cover the complete expected snapshot")
    for item in manifest[MANIFEST_FILES] + manifest[MANIFEST_EVIDENCE]:
        path = (directory / item[PATH_FIELD]).resolve()
        if directory.resolve() not in path.parents:
            raise ValueError("Manifest path escapes snapshot directory")
        if not path.is_file() or sha256(path) != item[HASH_FIELD]:
            raise ValueError(f"Snapshot integrity failure: {item[PATH_FIELD]}")
    return manifest


def verify_artifact(evidence, root):
    if not evidence.artifact_ref:
        return "Missing evidence reference"
    path = (root / evidence.artifact_ref).resolve()
    if root.resolve() not in path.parents:
        return "Evidence reference escapes project"
    if not path.is_file():
        return "Evidence file is missing"
    if sha256(path) != evidence.artifact_sha256:
        return "Evidence hash mismatch"
    return ""


def run(directory=DATA_DIR, output=OUTPUT_DIR, root=ROOT):
    directory, output, root = Path(directory), Path(output), Path(root)
    verify_manifest(directory)
    reserve_rows = load_records(directory / "reserve_ledger.csv", ReserveRow)
    positions = load_records(directory / "positions.csv", Position)
    trial_balance = load_records(directory / "trial_balance.csv", TrialBalanceRow)
    daily = load_records(directory / "daily_inputs.csv", DailyInput)
    population = load_records(directory / "control_population.csv", Evidence)
    covenants = load_records(directory / "covenants.csv", CovenantInput)
    vendors = load_records(directory / "vendors.csv", Vendor)
    responses = load_records(directory / "questionnaire.csv", Response)
    unique([asdict(item) for item in daily], DATE_KEYS)
    unique([asdict(item) for item in trial_balance], TRIAL_BALANCE_KEYS)
    unique([asdict(item) for item in population], EVIDENCE_KEYS)
    unique([asdict(item) for item in covenants], COVENANT_KEYS)
    unique([asdict(item) for item in vendors], VENDOR_KEYS)
    unique([asdict(item) for item in responses], RESPONSE_KEYS)
    if {item.vendor_id for item in responses} - {item.vendor_id for item in vendors}:
        raise ValueError("Questionnaire references an unknown vendor")
    expected_days = {item.date for item in daily}
    if not expected_days or any({item.date for item in collection} != expected_days
                                for collection in (reserve_rows, positions, trial_balance)):
        raise ValueError("Source dates do not cover the reporting calendar")
    reserve_results, reserve_details, capital_results, haircut_details = [], [], [], []
    reconciliations, variance_results, exceptions = [], [], []

    def reconcile(day, check, difference):
        status = "PASS" if abs(difference) <= MONEY_TOLERANCE else "FAIL"
        reconciliations.append(dict(zip(RECON_FIELDS, [day, check, difference, status])))
        if status == "FAIL":
            exceptions.append(exception_record(day, "RECON", check.replace(" ", "_"), "High",
                                                difference, "Difference within USD 0.01", "Reporting Control", "reconciliations.csv"))

    for inputs in sorted(daily, key=lambda item: item.date):
        day = inputs.date
        source = [item for item in reserve_rows if item.date == day]
        reserve_result, details = reserve(source, inputs.eligible_deposit)
        reserve_results.append(reserve_result)
        reserve_details.extend(details)
        balances = [item for item in trial_balance if item.date == day]
        by_account = {item.account: item for item in balances}
        if any(item.classification not in VALID_GL_CLASSES for item in balances):
            raise ValueError("Unmapped GL classification")
        if any(item.balance < 0 for item in balances if item.classification in (ASSET_CLASS, NONALLOWABLE_CLASS)):
            raise ValueError("Negative asset balance is unsupported")
        if any(item.balance > 0 for item in balances if item.classification == LIABILITY_CLASS):
            raise ValueError("Debit liability balance is unsupported")
        worth = -sum(item.balance for item in balances if item.classification == EQUITY_CLASS)
        nonallowable = sum(item.balance for item in balances if item.classification == NONALLOWABLE_CLASS)
        liabilities = -sum(item.balance for item in balances if item.classification == LIABILITY_CLASS)
        customer_payable = -sum(item.balance for item in balances if item.classification == LIABILITY_CLASS and item.account != OFFICE_ACCOUNT)
        day_positions = [item for item in positions if item.date == day]
        capital, haircuts = net_capital(day, worth, nonallowable, liabilities,
                                        reserve_result.required_reserve, inputs.eligible_deposit,
                                        customer_payable, day_positions)
        capital_results.append(capital)
        haircut_details.extend(haircuts)
        reconcile(day, "Trial balance", sum(item.balance for item in balances))
        reconcile(day, "Item 1 to GL", sum(item.amount for item in source if item.category in RESERVE_SOURCE_CATEGORIES)
                  + sum(item.balance for item in balances if item.account in RESERVE_GL_ACCOUNTS))
        reconcile(day, "Reserve deposit to GL", inputs.eligible_deposit - by_account[RESERVE_ACCOUNT].balance)
        reconcile(day, "Firm securities to GL", sum(item.market_value for item in day_positions) - by_account[SECURITIES_ACCOUNT].balance)
        if reserve_result.shortfall > MONEY_TOLERANCE:
            exceptions.append(exception_record(day, "RESERVE", "BROKER", "High", reserve_result.shortfall,
                                                "No reserve shortfall", "Treasury", "reserve_daily.csv"))
        if capital.excess_capital < 0:
            exceptions.append(exception_record(day, "CAPITAL", "BROKER", "High", capital.excess_capital,
                                                "Nonnegative excess capital", "Regulatory Reporting", "capital_daily.csv"))
        if len(reserve_results) > 1:
            metric_values = [("required_reserve", reserve_result.required_reserve, reserve_results[-2].required_reserve),
                             ("net_capital", capital.net_capital, capital_results[-2].net_capital)]
            for metric, current, previous in metric_values:
                delta, percent, flagged = variance(current, previous)
                variance_results.append(dict(zip(VARIANCE_FIELDS, [day, metric, current, previous, delta, percent, flagged])))
                if flagged:
                    exceptions.append(exception_record(day, "VARIANCE", metric, "Medium", delta,
                                                        "Below the configured variance trigger", "Reporting Control", "variance_controls.csv"))

    all_results = []
    artifact_results = []
    for item in population:
        tested = test_evidence(item)
        artifact_issue = verify_artifact(item, root)
        if artifact_issue:
            tested = replace(tested, result="FAIL", exceptions="; ".join(filter(None, [tested.exceptions, artifact_issue])),
                             deficiency_screen=deficiency(item.impact, item.likelihood, True), requires_judgment=True)
        artifact_results.append({"evidence_id": item.evidence_id, "artifact_ref": item.artifact_ref,
                                 "hash_status": "FAIL" if artifact_issue else "PASS", "issue": artifact_issue})
        all_results.append(tested)
        if tested.result != "PASS" or artifact_issue:
            exceptions.append(exception_record(item.date, "EVIDENCE", item.evidence_id, "Medium",
                                                tested.exceptions or artifact_issue, "Independent timely review and intact artifact",
                                                "Control Owner", item.artifact_ref))
    sample = select_sample(population, SAMPLE_SIZE, SEED)
    sampled_ids = {item.evidence_id for item in sample}
    sample_results = [item for item in all_results if item.evidence_id in sampled_ids]
    findings = []
    for result in sample_results:
        if result.result == "FAIL":
            findings.append(dict(zip(FINDING_FIELDS, [f"F-{result.evidence_id}", result.evidence_id,
                result.control_id, result.exceptions, "Independent timely review with evidence",
                "Not established: fictional case requires investigation", "Control evidence may not support execution",
                result.deficiency_screen, "Control Owner", "Investigate, remediate and retest",
                FINDING_DUE, "Judgment and approval pending"])))
    covenant_results = []
    evidence_results = {item.evidence_id: item for item in all_results}
    for covenant in covenants:
        matching = [item for item in population if item.control_id == f"COV-{covenant.borrower_id}" and item.date == covenant.date]
        if len(matching) != 1:
            raise ValueError("Expected one covenant evidence record per borrower and date")
        for result in evaluate_covenants(covenant, matching[0]):
            if evidence_results[result.evidence_id].result == "FAIL":
                result = replace(result, evidence_status="FAIL",
                                 overall_status="EVIDENCE EXCEPTION" if result.financial_status == "PASS" else result.financial_status)
            covenant_results.append(result)
            if result.overall_status != "PASS":
                exceptions.append(exception_record(result.date, "COVENANT", f"{result.borrower_id}-{result.metric.replace(' ', '_')}",
                    "High" if result.financial_status == "BREACH" else "Medium", result.overall_status,
                    result.limit, "Credit Control", result.evidence_id))
    vendor_results = [vendor_risk(vendor, [item for item in responses if item.vendor_id == vendor.vendor_id], AS_OF)
                      for vendor in vendors]
    for result in vendor_results:
        if result.review_status != "CURRENT" or result.residual_band == "High" or result.missing_evidence:
            exceptions.append(exception_record(AS_OF, "VENDOR", result.vendor_id, "High" if result.residual_band == "High" else "Medium",
                f"{result.review_status}; residual {result.residual_band}; missing {result.missing_evidence}",
                "Current review and complete evidence", result.owner, "vendor_reviews.csv"))
    contracts = json.loads((directory / LEASES_NAME).read_text(encoding="utf-8"))
    unique(contracts, LEASE_KEYS)
    lease_rows, journal_rows = [], []
    for contract in contracts:
        values = dict(contract)
        modification_values = values.pop(MODIFICATION_FIELD)
        values[PAYMENTS_FIELD] = tuple(values[PAYMENTS_FIELD])
        lease = Lease(**values)
        modification = None
        if modification_values:
            modification_values[REMAINING_PAYMENTS_FIELD] = tuple(modification_values[REMAINING_PAYMENTS_FIELD])
            modification = Modification(**modification_values)
        rows = schedule(lease, modification)
        lease_rows.extend(rows)
        entries = journals(lease, rows)
        journal_rows.extend(entries)
        reconcile(AS_OF, f"{lease.lease_id} ending liability", rows[-1].closing_liability)
        reconcile(AS_OF, f"{lease.lease_id} ending ROU", rows[-1].closing_rou)
        journal_ids = sorted({line.journal_id for line in entries})
        for identity in journal_ids:
            reconcile(AS_OF, identity, sum(line.debit - line.credit for line in entries if line.journal_id == identity))
    unique([asdict(item) for item in exceptions], ["exception_id"])
    outputs = {"reserve_daily.csv": reserve_results, "reserve_detail.csv": reserve_details,
               "capital_daily.csv": capital_results, "haircuts.csv": haircut_details,
               "covenant_compliance.csv": covenant_results, "control_test_results.csv": all_results,
               "control_sample.csv": sample, "sample_test_results.csv": sample_results,
               "vendor_reviews.csv": vendor_results, "lease_schedule.csv": lease_rows,
               "lease_journals.csv": journal_rows, "daily_exception_log.csv": exceptions}
    for filename, records in outputs.items():
        write_csv(output / filename, [asdict(item) for item in records], EXCEPTION_FIELDS if filename == "daily_exception_log.csv" else None)
    for filename, records, fields in [("reconciliations.csv", reconciliations, RECON_FIELDS),
                                       ("variance_controls.csv", variance_results, VARIANCE_FIELDS),
                                       ("findings.csv", findings, FINDING_FIELDS),
                                       ("evidence_integrity.csv", artifact_results, None)]:
        write_csv(output / filename, records, fields)
    summary = RunSummary(True, SEED, AS_OF, len(reserve_results), len(lease_rows), len(contracts),
                          len(population), len(sample), sum(item.result == "FAIL" for item in sample_results),
                          len(exceptions), sum(item[STATUS_FIELD] == "FAIL" for item in reconciliations))
    write_json(output / "run_summary.json", asdict(summary))
    write_json(output / "workbook_inputs.json", {"reserve_ledger": [asdict(item) for item in reserve_rows],
               "reserve_expected": [asdict(item) for item in reserve_results], "leases": contracts,
               "lease_expected": [asdict(item) for item in lease_rows], "summary": asdict(summary)})
    write_workpaper(output, summary, sample_results)
    source_manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    write_json(output / "run_manifest.json", {"synthetic": True, "seed": SEED,
               "source_manifest_sha256": sha256(directory / MANIFEST_NAME), "source_files": source_manifest[MANIFEST_FILES],
               "outputs": [{"path": path.name, "sha256": sha256(path)} for path in sorted(output.iterdir())
                           if path.is_file() and path.name not in ("run_manifest.json", "excel_verification.json")]})
    return summary


def write_workpaper(output, summary, results):
    lines = ["# Controls-testing workpaper", "", "Workpaper: CT-001. Period: October 2026. All evidence is synthetic.", "",
             "Objective: test independent, timely review and evidence completeness.",
             f"Population: {summary.population_size} records. Sample: {summary.sample_size}. Seed: {SEED}.",
             "Method: sort unique evidence IDs, then sample without replacement. Input order does not affect selection.",
             "This is a demonstration sample, not a statistical assurance conclusion.", "",
             "Procedures: inspect preparer, reviewer, date sequence, deadline, evidence reference and SHA-256.",
             "File existence and hashes are checked separately for the full population in evidence_integrity.csv.", "",
             f"Result: {summary.sample_failures} sampled records contain evidence exceptions.",
             "Deficiency screens require human judgment. No final significant-deficiency or material-weakness determination is made.", "",
             "| Evidence | Control | Result | Finding |", "| --- | --- | --- | --- |"]
    lines.extend(f"| {item.evidence_id} | {item.control_id} | {item.result} | {item.exceptions or 'None'} |" for item in results)
    lines.extend(["", "Preparer: pending. Reviewer: pending. Sign-off date: pending.",
                  "Follow-up: findings.csv contains owners, proposed actions and pending review. No remediation is asserted complete.", ""])
    (output / "controls_workpaper.md").write_text("\n".join(lines), encoding="utf-8")
