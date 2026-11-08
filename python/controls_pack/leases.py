"""Fixed end-of-period lessee schedules and consideration-only modification."""
from dataclasses import dataclass

from .common import number

# Configuration
KINDS = {"operating", "finance"}
ROUNDING_TOLERANCE = 1e-8


@dataclass(frozen=True)
class Lease:
    lease_id: str
    kind: str
    payments: tuple[float, ...]
    periodic_rate: float
    prepaid: float = 0.0
    incentive: float = 0.0
    initial_direct_cost: float = 0.0


@dataclass(frozen=True)
class Modification:
    effective_period: int
    remaining_payments: tuple[float, ...]
    periodic_rate: float
    change_type: str = "consideration_only"


@dataclass(frozen=True)
class LeasePeriod:
    lease_id: str
    kind: str
    period: int
    rate: float
    opening_liability: float
    remeasurement: float
    interest: float
    payment: float
    closing_liability: float
    opening_rou: float
    rou_adjustment: float
    rou_amortization: float
    closing_rou: float
    lease_expense: float


@dataclass(frozen=True)
class JournalLine:
    journal_id: str
    lease_id: str
    period: int
    event: str
    account: str
    debit: float
    credit: float


def present_value(payments, periodic_rate):
    rate = number(periodic_rate, "periodic_rate", 0)
    values = tuple(number(payment, "payment", 0) for payment in payments)
    if not values:
        raise ValueError("Lease must contain payments")
    return sum(payment / (1 + rate) ** period for period, payment in enumerate(values, 1))


def schedule(lease, modification=None):
    if lease.kind not in KINDS or not lease.lease_id:
        raise ValueError("Invalid lease kind or ID")
    payments = tuple(number(payment, "payment", 0) for payment in lease.payments)
    rate = number(lease.periodic_rate, "periodic_rate", 0)
    liability = present_value(payments, rate)
    adjustment = (number(lease.prepaid, "prepaid", 0) - number(lease.incentive, "incentive", 0)
                  + number(lease.initial_direct_cost, "initial_direct_cost", 0))
    rou = liability + adjustment
    if rou < 0:
        raise ValueError("Negative initial ROU is unsupported")
    if modification:
        period = modification.effective_period
        if (type(period) is not int or not 1 <= period <= len(payments)
                or modification.change_type != "consideration_only"):
            raise ValueError("Only in-term consideration-only modifications are supported")
        if len(modification.remaining_payments) != len(payments) - period + 1:
            raise ValueError("Consideration-only modification cannot change term")
        present_value(modification.remaining_payments, modification.periodic_rate)
    expense = (sum(payments) + adjustment) / len(payments)
    amortization = rou / len(payments)
    rows = []
    for period in range(1, len(payments) + 1):
        opening_liability, opening_rou = liability, rou
        delta = 0.0
        if modification and period == modification.effective_period:
            rate = number(modification.periodic_rate, "periodic_rate", 0)
            payments = payments[:period - 1] + tuple(float(value) for value in modification.remaining_payments)
            delta = present_value(modification.remaining_payments, rate) - liability
            liability += delta
            rou += delta
            if rou < 0:
                raise ValueError("Modification reducing ROU below zero is unsupported")
            remaining = len(payments) - period + 1
            expense = (sum(payments[period - 1:]) + rou - liability) / remaining
            amortization = rou / remaining
        interest = liability * rate
        payment = payments[period - 1]
        liability += interest - payment
        rou_amortization = expense - interest if lease.kind == "operating" else amortization
        total_expense = expense if lease.kind == "operating" else interest + rou_amortization
        rou -= rou_amortization
        if abs(liability) < ROUNDING_TOLERANCE:
            liability = 0.0
        if abs(rou) < ROUNDING_TOLERANCE:
            rou = 0.0
        rows.append(LeasePeriod(lease.lease_id, lease.kind, period, rate, opening_liability,
                                delta, interest, payment, liability, opening_rou,
                                delta, rou_amortization, rou, total_expense))
    return rows


def journals(lease, rows):
    liability = present_value(lease.payments, lease.periodic_rate)
    rou = liability + lease.prepaid - lease.incentive + lease.initial_direct_cost
    lines = []

    def entry(period, event, account, signed_debit):
        lines.append(JournalLine(f"{lease.lease_id}-{period:03d}-{event}", lease.lease_id,
                                 period, event, account, max(signed_debit, 0), max(-signed_debit, 0)))

    entry(0, "commencement", "ROU asset", rou)
    entry(0, "commencement", "Lease liability", -liability)
    entry(0, "commencement", "Cash", -(lease.prepaid + lease.initial_direct_cost - lease.incentive))
    for row in rows:
        if row.remeasurement:
            entry(row.period, "modification", "ROU asset", row.rou_adjustment)
            entry(row.period, "modification", "Lease liability", -row.remeasurement)
        if lease.kind == "operating":
            entry(row.period, "accrual", "Operating lease expense", row.lease_expense)
            entry(row.period, "accrual", "Lease liability", -row.interest)
            entry(row.period, "accrual", "ROU asset", -row.rou_amortization)
        else:
            entry(row.period, "accrual", "Interest expense", row.interest)
            entry(row.period, "accrual", "Lease liability", -row.interest)
            entry(row.period, "amortization", "ROU amortization expense", row.rou_amortization)
            entry(row.period, "amortization", "ROU asset", -row.rou_amortization)
        entry(row.period, "payment", "Lease liability", row.payment)
        entry(row.period, "payment", "Cash", -row.payment)
    return lines
