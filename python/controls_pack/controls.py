"""Internal-policy evidence checks, samples, findings and daily exceptions."""
import random
from dataclasses import dataclass
from datetime import date, timedelta

from .common import number, unique
from .config import (IMPORTANT_IMPACT, MATERIAL_IMPACT, REASONABLE_POSSIBILITY,
                     VARIANCE_AMOUNT, VARIANCE_PERCENT)

# Configuration
POPULATION_KEYS = ["evidence_id"]
OPEN_STATUS = "OPEN"
REMEDIATION_DAYS = 5
VALID_RATINGS = range(1, 6)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    date: str
    control_id: str
    preparer: str
    reviewer: str
    prepared_on: str
    reviewed_on: str
    due_on: str
    artifact_ref: str
    artifact_sha256: str
    impact: int = 1
    likelihood: int = 1


@dataclass(frozen=True)
class TestResult:
    evidence_id: str
    control_id: str
    date: str
    result: str
    exceptions: str
    deficiency_screen: str
    requires_judgment: bool


@dataclass(frozen=True)
class ExceptionRecord:
    exception_id: str
    date: str
    control_id: str
    entity_id: str
    severity: str
    observed: str
    expected: str
    owner: str
    due_on: str
    status: str
    evidence_ref: str
    resolution: str = ""


def deficiency(impact, likelihood, failed):
    if type(impact) is not int or type(likelihood) is not int or impact not in VALID_RATINGS or likelihood not in VALID_RATINGS:
        raise ValueError("Impact and likelihood must be integer ratings from 1 to 5")
    if not failed:
        return "No exception"
    if impact >= MATERIAL_IMPACT and likelihood >= REASONABLE_POSSIBILITY:
        return "Potential material weakness: judgment required"
    if impact >= IMPORTANT_IMPACT:
        return "Potential significant deficiency: judgment required"
    return "Control deficiency: judgment required"


def test_evidence(evidence):
    issues = []
    if not evidence.preparer or not evidence.reviewer:
        issues.append("Missing preparer or reviewer")
    elif evidence.preparer == evidence.reviewer:
        issues.append("Reviewer is not independent")
    if not evidence.artifact_ref or not evidence.artifact_sha256:
        issues.append("Missing evidence artifact or hash")
    elif len(evidence.artifact_sha256) != 64 or any(c not in "0123456789abcdef" for c in evidence.artifact_sha256):
        issues.append("Invalid artifact hash")
    try:
        performed = date.fromisoformat(evidence.date)
        prepared = date.fromisoformat(evidence.prepared_on)
        reviewed = date.fromisoformat(evidence.reviewed_on)
        due = date.fromisoformat(evidence.due_on)
        if prepared < performed or reviewed < prepared:
            issues.append("Evidence dates out of order")
        if reviewed > due:
            issues.append("Review past due")
    except ValueError:
        issues.append("Missing or invalid evidence dates")
    failed = bool(issues)
    return TestResult(evidence.evidence_id, evidence.control_id, evidence.date,
                      "FAIL" if failed else "PASS", "; ".join(issues),
                      deficiency(evidence.impact, evidence.likelihood, failed), failed)


def select_sample(population, sample_size, seed):
    population = list(population)
    unique([vars(item) for item in population], POPULATION_KEYS)
    if type(sample_size) is not int or not 0 < sample_size <= len(population):
        raise ValueError("Sample size must be positive and no greater than population")
    ordered = sorted(population, key=lambda item: item.evidence_id)
    return sorted(random.Random(seed).sample(ordered, sample_size), key=lambda item: item.evidence_id)


def variance(current, previous):
    current = number(current, "current")
    previous = number(previous, "previous")
    delta = current - previous
    percent = delta / abs(previous) if previous else None
    exception = abs(delta) >= VARIANCE_AMOUNT and (percent is None or abs(percent) >= VARIANCE_PERCENT)
    return delta, percent, exception


def exception_record(run_date, control_id, entity_id, severity, observed, expected, owner, evidence_ref):
    due = (date.fromisoformat(run_date) + timedelta(days=REMEDIATION_DAYS)).isoformat()
    observed = f"{observed:.2f}" if isinstance(observed, (int, float)) else str(observed)
    expected = f"{expected:.2f}" if isinstance(expected, (int, float)) else str(expected)
    return ExceptionRecord(f"{run_date}-{control_id}-{entity_id}", run_date, control_id, entity_id,
                           severity, observed, expected, owner, due, OPEN_STATUS, evidence_ref)
