"""Fictional quarterly covenant definitions and evidence status."""
from dataclasses import dataclass

from .common import number
from .config import INTEREST_COVER_MIN, LEVERAGE_MAX, LIQUIDITY_MIN
from .controls import test_evidence

# Configuration
PASS = "PASS"
BREACH = "BREACH"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class CovenantInput:
    borrower_id: str
    date: str
    debt: float
    unrestricted_cash: float
    undrawn_committed: float
    ttm_ebitda: float
    ttm_interest: float


@dataclass(frozen=True)
class CovenantResult:
    borrower_id: str
    date: str
    metric: str
    actual: float | None
    limit: float
    headroom: float | None
    financial_status: str
    evidence_status: str
    overall_status: str
    evidence_id: str


def evaluate_covenants(item, evidence):
    debt = number(item.debt, "debt", 0)
    cash = number(item.unrestricted_cash, "unrestricted_cash", 0)
    undrawn = number(item.undrawn_committed, "undrawn_committed", 0)
    ebitda = number(item.ttm_ebitda, "ttm_ebitda")
    interest = number(item.ttm_interest, "ttm_interest", 0)
    if evidence.date != item.date or evidence.control_id != f"COV-{item.borrower_id}":
        raise ValueError("Covenant evidence does not match borrower and period")
    evidence_status = test_evidence(evidence).result
    metrics = [("Net leverage", max(debt - cash, 0) / ebitda if ebitda > 0 else None, LEVERAGE_MAX, False),
               ("Interest cover", ebitda / interest if interest > 0 else None, INTEREST_COVER_MIN, True),
               ("Minimum liquidity", cash + undrawn, LIQUIDITY_MIN, True)]
    results = []
    for metric, actual, limit, is_minimum in metrics:
        headroom = None if actual is None else (actual - limit if is_minimum else limit - actual)
        status = UNAVAILABLE if headroom is None else (PASS if headroom >= 0 else BREACH)
        overall = status if status != PASS else (PASS if evidence_status == PASS else "EVIDENCE EXCEPTION")
        results.append(CovenantResult(item.borrower_id, item.date, metric, actual, limit,
                                      headroom, status, evidence_status, overall, evidence.evidence_id))
    return results
