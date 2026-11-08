"""Restricted customer reserve and basic net capital calculations."""
from dataclasses import dataclass

from .common import number, unique
from .config import (AI_LIMIT, CAPITAL_FLOOR, CONCENTRATION_LIMIT, EQUITY_HAIRCUT,
                     ITEM10_REDUCTION, MONEY_FUND_HAIRCUT)

# Configuration
RESERVE_ITEMS = {"free_credit": 1, "customer_draft": 1, "overdrawn_check": 1,
                 "borrowed_money": 2, "securities_loaned": 3, "failed_receive": 4,
                 "principal_sale": 5, "distribution": 6, "short_count": 7,
                 "suspense": 8, "transfer": 9, "customer_debit": 10,
                 "securities_borrowed": 11, "failed_deliver": 12}
SUPPORTED_CLASSES = {"listed_equity": EQUITY_HAIRCUT, "qualifying_money_fund": MONEY_FUND_HAIRCUT}
RESERVE_KEYS = ["record_id"]
POSITION_KEYS = ["position_id"]
CASH_ACCOUNT = "cash"
LONG_SIDE = "long"


@dataclass(frozen=True)
class ReserveRow:
    record_id: str
    date: str
    category: str
    amount: float
    age_days: int = 0
    market_value: float = 0
    secured: bool = True
    collectible: bool = True
    affiliate: bool = False
    account_type: str = "cash"
    transfer_confirmed: bool = False


@dataclass(frozen=True)
class ReserveLine:
    record_id: str
    date: str
    item: int
    credit: float
    debit: float
    exclusion: str


@dataclass(frozen=True)
class ReserveResult:
    date: str
    credits: float
    raw_debits: float
    item10: float
    debit_reduction: float
    allowed_debits: float
    required_reserve: float
    eligible_deposit: float
    shortfall: float
    excess_deposit: float


def reserve(rows, eligible_deposit):
    rows = list(rows)
    if not rows:
        raise ValueError("Reserve population is empty")
    unique([vars(row) for row in rows], RESERVE_KEYS)
    dates = {row.date for row in rows}
    if len(dates) != 1:
        raise ValueError("Reserve population must contain exactly one date")
    deposit = number(eligible_deposit, "eligible_deposit", 0)
    lines = []
    for row in rows:
        if row.category not in RESERVE_ITEMS:
            raise ValueError(f"Unsupported reserve category: {row.category}")
        amount = number(row.amount, "amount", 0)
        market = number(row.market_value, "market_value", 0)
        age = number(row.age_days, "age_days", 0)
        if not age.is_integer():
            raise ValueError("age_days must be an integer")
        if any(type(value) is not bool for value in
               (row.secured, row.collectible, row.affiliate, row.transfer_confirmed)):
            raise ValueError("Reserve eligibility flags must be boolean")
        item = RESERVE_ITEMS[row.category]
        exclusion = ""
        if item == 3:
            amount = max(amount, market)
        if item == 4 and age > 30:
            amount = max(amount, market)
        if item in (6, 7, 8) and age <= 30:
            amount, exclusion = 0.0, "Not over 30 calendar days"
        elif item in (6, 7, 8):
            amount = market
        if item == 9:
            if age <= 40 or row.transfer_confirmed:
                amount, exclusion = 0.0, "Transfer age or confirmation exclusion"
            else:
                amount = market
        if item == 10:
            if row.account_type != CASH_ACCOUNT:
                raise ValueError("Only cash customer debit accounts are supported")
            if not row.secured or not row.collectible or row.affiliate:
                amount, exclusion = 0.0, "Unsecured, doubtful or affiliated debit"
        if item == 12 and age > 30:
            amount, exclusion = 0.0, "Fail older than 30 calendar days"
        lines.append(ReserveLine(row.record_id, row.date, item,
                                 amount if item <= 9 else 0.0,
                                 amount if item >= 10 else 0.0, exclusion))
    credits = sum(line.credit for line in lines)
    debits = sum(line.debit for line in lines)
    item10 = sum(line.debit for line in lines if line.item == 10)
    reduction = item10 * ITEM10_REDUCTION
    allowed = debits - reduction
    required = max(credits - allowed, 0.0)
    result = ReserveResult(rows[0].date, credits, debits, item10, reduction, allowed,
                           required, deposit, max(required - deposit, 0.0),
                           max(deposit - required, 0.0))
    return result, lines


@dataclass(frozen=True)
class Position:
    position_id: str
    date: str
    issuer: str
    asset_class: str
    market_value: float
    side: str = "long"


@dataclass(frozen=True)
class Haircut:
    position_id: str
    date: str
    issuer: str
    market_value: float
    rate: float
    deduction: float


@dataclass(frozen=True)
class CapitalResult:
    date: str
    net_worth: float
    nonallowable: float
    tentative_net_capital: float
    haircuts: float
    net_capital: float
    aggregate_liabilities: float
    reserve_exclusion: float
    aggregate_indebtedness: float
    required_capital: float
    excess_capital: float
    status: str


def net_capital(date, net_worth, nonallowable, aggregate_liabilities,
                reserve_requirement, eligible_deposit, customer_payable, positions):
    worth = number(net_worth, "net_worth")
    deduction = number(nonallowable, "nonallowable", 0)
    liabilities = number(aggregate_liabilities, "aggregate_liabilities", 0)
    required = number(reserve_requirement, "reserve_requirement", 0)
    deposit = number(eligible_deposit, "eligible_deposit", 0)
    payable = number(customer_payable, "customer_payable", 0)
    if payable > liabilities:
        raise ValueError("Customer payable exceeds aggregate liabilities")
    tentative = worth - deduction
    positions = list(positions)
    unique([vars(position) for position in positions], POSITION_KEYS)
    exposures = {}
    for position in positions:
        value = number(position.market_value, "market_value", 0)
        if position.date != date or not position.issuer:
            raise ValueError("Position date mismatch or missing issuer")
        if position.side != LONG_SIDE or position.asset_class not in SUPPORTED_CLASSES:
            raise ValueError("Only unhedged long equities and qualifying money funds are supported")
        if position.asset_class == "listed_equity":
            exposures[position.issuer] = exposures.get(position.issuer, 0.0) + value
    if any(value > max(tentative, 0) * CONCENTRATION_LIMIT for value in exposures.values()):
        raise ValueError("Issuer concentration requires an unsupported additional haircut")
    haircuts = [Haircut(position.position_id, date, position.issuer, float(position.market_value),
                        SUPPORTED_CLASSES[position.asset_class],
                        float(position.market_value) * SUPPORTED_CLASSES[position.asset_class])
                for position in positions]
    total_haircuts = sum(line.deduction for line in haircuts)
    capital = tentative - total_haircuts
    exclusion = min(liabilities, required, deposit, payable)
    indebtedness = liabilities - exclusion
    requirement = max(CAPITAL_FLOOR, indebtedness / AI_LIMIT)
    excess = capital - requirement
    return CapitalResult(date, worth, deduction, tentative, total_haircuts, capital,
                         liabilities, exclusion, indebtedness, requirement, excess,
                         "PASS" if excess >= 0 else "BREACH"), haircuts
