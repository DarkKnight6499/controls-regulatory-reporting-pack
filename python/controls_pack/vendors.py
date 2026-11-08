"""Fictional third-party tiering and evidence-weighted questionnaire scores."""
from dataclasses import dataclass
from datetime import date, timedelta

from .common import number
from .config import QUESTION_WEIGHTS, REVIEW_DAYS, VENDOR_HIGH, VENDOR_MEDIUM

# Configuration
RATING_MAX = 5
RESIDUAL_HIGH = 2.5
RESIDUAL_MEDIUM = 1.0


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    service: str
    owner: str
    criticality: int
    data_sensitivity: int
    substitutability: int
    last_review: str


@dataclass(frozen=True)
class Response:
    vendor_id: str
    question_id: str
    answer: int | None
    evidence_ref: str


@dataclass(frozen=True)
class VendorResult:
    vendor_id: str
    service: str
    owner: str
    inherent_risk: float
    tier: str
    questionnaire_score: float
    missing_evidence: int
    residual_risk: float
    residual_band: str
    last_review: str
    next_review: str
    review_status: str


def vendor_risk(vendor, responses, as_of):
    ratings = [vendor.criticality, vendor.data_sensitivity, vendor.substitutability]
    if any(type(value) is not int or not 1 <= value <= RATING_MAX for value in ratings):
        raise ValueError("Vendor ratings must be integers from 1 to 5")
    inherent = sum(ratings) / len(ratings)
    tier = "Tier 1" if inherent >= VENDOR_HIGH else ("Tier 2" if inherent >= VENDOR_MEDIUM else "Tier 3")
    by_question = {}
    for response in responses:
        if response.vendor_id != vendor.vendor_id or response.question_id not in QUESTION_WEIGHTS:
            raise ValueError("Questionnaire vendor or question mismatch")
        if response.question_id in by_question:
            raise ValueError("Duplicate questionnaire response")
        if response.answer is not None and (type(response.answer) is not int or not 0 <= response.answer <= RATING_MAX):
            raise ValueError("Questionnaire answer must be an integer from 0 to 5")
        by_question[response.question_id] = response
    weighted = 0.0
    missing = 0
    for question, weight in QUESTION_WEIGHTS.items():
        response = by_question.get(question)
        if response is None or response.answer is None or not response.evidence_ref:
            missing += 1
            continue
        weighted += number(response.answer, "answer", 0) / RATING_MAX * weight
    score = weighted / sum(QUESTION_WEIGHTS.values())
    residual = inherent * (1 - score)
    band = "High" if residual >= RESIDUAL_HIGH else ("Medium" if residual >= RESIDUAL_MEDIUM else "Low")
    today, reviewed = date.fromisoformat(as_of), date.fromisoformat(vendor.last_review)
    if reviewed > today:
        raise ValueError("Last review cannot be in the future")
    next_review = reviewed + timedelta(days=REVIEW_DAYS[tier])
    return VendorResult(vendor.vendor_id, vendor.service, vendor.owner, inherent, tier, score,
                         missing, residual, band, vendor.last_review, next_review.isoformat(),
                         "OVERDUE" if next_review < today else "DUE TODAY" if next_review == today else "CURRENT")
