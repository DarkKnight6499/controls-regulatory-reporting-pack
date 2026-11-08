"""Reproducible fictional source population. This module performs no network I/O."""
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from .common import sha256, write_csv, write_json
from .config import (AS_OF, BUSINESS_DAYS, DATA_DIR, QUESTION_WEIGHTS, SEED, START_DATE)
from .controls import Evidence
from .covenants import CovenantInput
from .regulatory import Position, ReserveRow
from .vendors import Response, Vendor

# Configuration
SNAPSHOT_FILES = ("reserve_ledger.csv", "positions.csv", "trial_balance.csv", "daily_inputs.csv",
                  "covenants.csv", "control_population.csv", "vendors.csv", "questionnaire.csv", "leases.json")
FIXED_ASSETS = 200_000.0
PREPAID_ASSETS = 50_000.0
OFFICE_PAYABLE = 500_000.0
BASE_NET_WORTH = 2_000_000.0
CUSTOMER_CREDIT = 3_000_000
CUSTOMER_DEBIT = 1_000_000
EQUITY_LOTS = 6
EQUITY_POSITION = 50_000
MONEY_FUND_POSITION = 100_000
HIGH_EXPOSURE_DAY = 6
CAPITAL_STRESS_DAY = 8
STRESS_EQUITY_POSITION = 10000
STRESS_NET_WORTH = 450000.0
CREDIT_JITTER = 50000
DEBIT_JITTER = 25000
POSITION_JITTER = 2000
WORTH_JITTER = 25000
DEPOSIT = 2_300_000.0
RESERVE_STRESS = 500000
STATIC_RESERVE_ROWS = [
    dict(category="customer_draft", amount=20000), dict(category="borrowed_money", amount=100000),
    dict(category="securities_loaned", amount=50000, market_value=55000),
    dict(category="failed_receive", amount=30000, market_value=32000, age_days=31),
    dict(category="principal_sale", amount=5000), dict(category="distribution", amount=0, market_value=2000, age_days=31),
    dict(category="short_count", amount=0, market_value=1000, age_days=30),
    dict(category="suspense", amount=0, market_value=1500, age_days=31),
    dict(category="transfer", amount=0, market_value=2500, age_days=41),
]
STATIC_DEBIT_ROWS = [dict(category="customer_debit", amount=10000, secured=False),
                     dict(category="customer_debit", amount=8000, collectible=False),
                     dict(category="customer_debit", amount=6000, affiliate=True),
                     dict(category="securities_borrowed", amount=25000),
                     dict(category="failed_deliver", amount=15000, age_days=30),
                     dict(category="failed_deliver", amount=7000, age_days=31)]
COVENANT_CASES = [dict(borrower_id="ALPHA", debt=4_500_000, unrestricted_cash=600000, undrawn_committed=100000, ttm_ebitda=1_200_000, ttm_interest=250000),
                  dict(borrower_id="BETA", debt=6_000_000, unrestricted_cash=100000, undrawn_committed=100000, ttm_ebitda=1_000_000, ttm_interest=400000),
                  dict(borrower_id="GAMMA", debt=2_000_000, unrestricted_cash=700000, undrawn_committed=0, ttm_ebitda=-100000, ttm_interest=0)]
VENDOR_CASES = [dict(vendor_id="V001", service="Hosted ledger", owner="Technology Risk", criticality=5, data_sensitivity=5, substitutability=4, last_review="2026-06-01"),
                dict(vendor_id="V002", service="Payments", owner="Treasury", criticality=5, data_sensitivity=4, substitutability=4, last_review="2026-10-01"),
                dict(vendor_id="V003", service="Market data", owner="Market Risk", criticality=3, data_sensitivity=2, substitutability=3, last_review="2026-02-01"),
                dict(vendor_id="V004", service="Office supplies", owner="Operations", criticality=1, data_sensitivity=1, substitutability=1, last_review="2026-07-01"),
                dict(vendor_id="V005", service="Document archive", owner="Compliance", criticality=3, data_sensitivity=4, substitutability=3, last_review="2026-03-01")]
STATIC_GL_ACCOUNTS = [dict(account="Fixed assets", classification="nonallowable", balance=FIXED_ASSETS),
                      dict(account="Prepaid expenses", classification="nonallowable", balance=PREPAID_ASSETS),
                      dict(account="Customer drafts", classification="liability", balance=-20000),
                      dict(account="Other customer payables", classification="liability", balance=-185000),
                      dict(account="Office payable", classification="liability", balance=-OFFICE_PAYABLE)]
STATIC_PAYABLE_TOTAL = 205000
STATIC_RECEIVABLE_TOTAL = 71000
MISSING_EVIDENCE_INTERVAL = 13
SELF_REVIEW_INTERVAL = 11
LATE_REVIEW_INTERVAL = 7
HIGH_IMPACT_INTERVAL = 3
MISSING_VENDOR = "V001"
MISSING_QUESTIONS = {"security", "continuity"}
CONSERVATIVE_RECEIVABLE_DEDUCTION = 31000
EVIDENCE_CONTROL_IDS = ("RESERVE", "CAPITAL", "LEASE", "VENDOR")
LEASE_CONTRACTS = [
    {"lease_id": "OFFICE-01", "kind": "operating", "payments": [10000.0] * 12 + [11000.0] * 12,
     "periodic_rate": 0.005, "prepaid": 2000.0, "incentive": 1000.0, "initial_direct_cost": 500.0,
     "modification": {"effective_period": 13, "remaining_payments": [12500.0] * 12,
                      "periodic_rate": 0.006, "change_type": "consideration_only"}},
    {"lease_id": "EQUIP-01", "kind": "finance", "payments": [5000.0] * 18,
     "periodic_rate": 0.004, "prepaid": 0.0, "incentive": 0.0, "initial_direct_cost": 1000.0,
     "modification": None},
    {"lease_id": "SYSTEM-01", "kind": "finance", "payments": [3000.0] * 12,
     "periodic_rate": 0.003, "prepaid": 500.0, "incentive": 0.0, "initial_direct_cost": 0.0,
     "modification": {"effective_period": 7, "remaining_payments": [3300.0] * 6,
                      "periodic_rate": 0.004, "change_type": "consideration_only"}},
]


@dataclass(frozen=True)
class TrialBalanceRow:
    date: str
    account: str
    classification: str
    balance: float


@dataclass(frozen=True)
class DailyInput:
    date: str
    eligible_deposit: float


def generate_snapshot(directory=DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    days = []
    current = date.fromisoformat(START_DATE)
    while len(days) < BUSINESS_DAYS:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    ledger, positions, trial_balance, daily, evidence = [], [], [], [], []

    def make_evidence(identity, day, control, index):
        artifact = directory / "evidence" / f"{identity}.json"
        write_json(artifact, {"synthetic": True, "evidence_id": identity, "control_id": control,
                              "date": day, "action": "Prepared and reviewed fictional calculation"})
        missing = index % MISSING_EVIDENCE_INTERVAL == 0
        reviewer = "Maker-A" if index % SELF_REVIEW_INTERVAL == 0 else "Checker-B"
        reviewed = (date.fromisoformat(day) + timedelta(days=2 if index % LATE_REVIEW_INTERVAL == 0 else 0)).isoformat()
        return Evidence(identity, day, control, "Maker-A", reviewer, day, reviewed, day,
                        "" if missing else f"data/synthetic/evidence/{identity}.json",
                        "" if missing else sha256(artifact), 4 if index % HIGH_IMPACT_INTERVAL == 0 else 2, 3)

    for index, day in enumerate(days):
        credit = CUSTOMER_CREDIT + rng.randint(-CREDIT_JITTER, CREDIT_JITTER) + (RESERVE_STRESS if index == HIGH_EXPOSURE_DAY else 0)
        debit = CUSTOMER_DEBIT + rng.randint(-DEBIT_JITTER, DEBIT_JITTER)
        specs = [dict(category="free_credit", amount=credit)] + STATIC_RESERVE_ROWS + [dict(category="customer_debit", amount=debit)] + STATIC_DEBIT_ROWS
        day_rows = [ReserveRow(record_id=f"R-{day}-{ordinal:02d}", date=day, **specification)
                    for ordinal, specification in enumerate(specs, 1)]
        ledger.extend(day_rows)
        daily.append(DailyInput(day, DEPOSIT))
        day_positions = [Position(f"P-{day}-{lot}", day, f"Issuer-{lot}", "listed_equity",
                                  (STRESS_EQUITY_POSITION if index == CAPITAL_STRESS_DAY else EQUITY_POSITION) + rng.randint(-POSITION_JITTER, POSITION_JITTER))
                         for lot in range(EQUITY_LOTS)]
        day_positions.append(Position(f"P-{day}-fund", day, "Money Fund", "qualifying_money_fund", MONEY_FUND_POSITION))
        positions.extend(day_positions)
        worth = STRESS_NET_WORTH if index == CAPITAL_STRESS_DAY else BASE_NET_WORTH + rng.randint(-WORTH_JITTER, WORTH_JITTER)
        liabilities = credit + STATIC_PAYABLE_TOTAL + OFFICE_PAYABLE
        receivables = debit + STATIC_RECEIVABLE_TOTAL
        firm_securities = sum(position.market_value for position in day_positions)
        cash = worth + liabilities - DEPOSIT - receivables - firm_securities - FIXED_ASSETS - PREPAID_ASSETS
        accounts = [dict(account="Operating cash", classification="asset", balance=cash),
                    dict(account="Reserve deposit", classification="asset", balance=DEPOSIT),
                    dict(account="Customer receivables", classification="asset", balance=receivables - CONSERVATIVE_RECEIVABLE_DEDUCTION),
                    dict(account="Receivables conservatively deducted", classification="nonallowable", balance=CONSERVATIVE_RECEIVABLE_DEDUCTION),
                    dict(account="Firm securities", classification="asset", balance=firm_securities),
                    dict(account="Customer free credit", classification="liability", balance=-credit),
                    dict(account="Equity", classification="equity", balance=-worth)] + STATIC_GL_ACCOUNTS
        trial_balance.extend(TrialBalanceRow(date=day, **account) for account in accounts)
        for control in EVIDENCE_CONTROL_IDS:
            count = len(evidence) + 1
            evidence.append(make_evidence(f"E{count:03d}", day, control, count))

    covenant_rows = [CovenantInput(date=AS_OF, **case) for case in COVENANT_CASES]
    for item in covenant_rows:
        count = len(evidence) + 1
        evidence.append(make_evidence(f"E{count:03d}", item.date, f"COV-{item.borrower_id}", count))
    vendor_rows = [Vendor(**case) for case in VENDOR_CASES]
    responses = []
    for vendor in vendor_rows:
        for question in QUESTION_WEIGHTS:
            answer = rng.randint(1, 5)
            missing = vendor.vendor_id == MISSING_VENDOR and question in MISSING_QUESTIONS
            evidence_ref = "" if missing else f"data/synthetic/vendor_evidence/{vendor.vendor_id}-{question}.json"
            if evidence_ref:
                write_json(directory / "vendor_evidence" / f"{vendor.vendor_id}-{question}.json",
                           {"synthetic": True, "vendor_id": vendor.vendor_id, "question_id": question, "answer": answer})
            responses.append(Response(vendor.vendor_id, question, answer, evidence_ref))
    for filename, records in [("reserve_ledger.csv", ledger), ("positions.csv", positions),
                               ("trial_balance.csv", trial_balance), ("daily_inputs.csv", daily),
                               ("covenants.csv", covenant_rows), ("control_population.csv", evidence),
                               ("vendors.csv", vendor_rows), ("questionnaire.csv", responses)]:
        write_csv(directory / filename, [asdict(record) for record in records])
    write_json(directory / "leases.json", LEASE_CONTRACTS)
    manifest = {"synthetic": True, "seed": SEED, "as_of": AS_OF,
                "generator": "controls_pack.synthetic.generate_snapshot", "unit": "USD",
                "files": [{"path": filename, "sha256": sha256(directory / filename)} for filename in SNAPSHOT_FILES],
                "evidence_files": [{"path": str(path.relative_to(directory)).replace(chr(92), "/"), "sha256": sha256(path)}
                                   for path in sorted(directory.glob("**/*.json"))
                                   if path.parent.name in ("evidence", "vendor_evidence")]}
    write_json(directory / "manifest.json", manifest)
