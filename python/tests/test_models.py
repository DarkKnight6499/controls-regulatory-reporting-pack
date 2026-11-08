import unittest
from dataclasses import replace

from controls_pack.controls import Evidence, deficiency, select_sample, test_evidence, variance
from controls_pack.covenants import CovenantInput, evaluate_covenants
from controls_pack.leases import Lease, Modification, journals, present_value, schedule
from controls_pack.regulatory import Position, ReserveRow, net_capital, reserve
from controls_pack.vendors import Response, Vendor, vendor_risk

# Configuration
DAY = "2026-10-30"
GOOD_EVIDENCE = Evidence("E1", DAY, "COV-A", "Maker", "Checker", DAY, DAY, DAY,
                         "data/synthetic/evidence/E1.json", "a" * 64, 4, 3)


class ReserveTests(unittest.TestCase):
    def row(self, identity, category, amount, **kwargs):
        return ReserveRow(identity, DAY, category, amount, **kwargs)

    def test_hand_computed_reserve_and_reduction(self):
        result, lines = reserve([self.row("1", "free_credit", 1000),
                                 self.row("2", "customer_debit", 200),
                                 self.row("3", "securities_borrowed", 100)], 600)
        self.assertEqual((result.credits, result.allowed_debits), (1000, 298))
        self.assertEqual((result.required_reserve, result.shortfall), (702, 102))
        self.assertEqual(len(lines), 3)

    def test_age_boundaries_and_valuation(self):
        rows = [self.row("1", "free_credit", 1000),
                self.row("2", "short_count", 10, market_value=20, age_days=30),
                self.row("3", "short_count", 10, market_value=20, age_days=31),
                self.row("4", "failed_deliver", 100, age_days=30),
                self.row("5", "failed_deliver", 100, age_days=31),
                self.row("6", "failed_receive", 30, market_value=50, age_days=31),
                self.row("7", "securities_loaned", 40, market_value=60)]
        result, _ = reserve(rows, 2000)
        self.assertEqual(result.credits, 1130)
        self.assertEqual(result.required_reserve, 1030)
        self.assertEqual(result.excess_deposit, 970)

    def test_transfer_boundary_and_confirmation(self):
        rows = [self.row("1", "transfer", 0, market_value=10, age_days=40),
                self.row("2", "transfer", 0, market_value=20, age_days=41),
                self.row("3", "transfer", 0, market_value=30, age_days=41, transfer_confirmed=True)]
        self.assertEqual(reserve(rows, 0)[0].credits, 20)

    def test_cash_exclusions_and_zero_floor(self):
        rows = [self.row("1", "customer_debit", 100, secured=False),
                self.row("2", "customer_debit", 100, collectible=False),
                self.row("3", "customer_debit", 100, affiliate=True),
                self.row("4", "customer_debit", 100)]
        result, _ = reserve(rows, 0)
        self.assertEqual((result.item10, result.required_reserve), (100, 0))

    def test_bad_or_unsupported_population(self):
        cases = [[], [self.row("1", "occ_margin", 10)],
                 [self.row("1", "customer_debit", 10, account_type="margin")],
                 [self.row("1", "free_credit", -1)],
                 [self.row("1", "free_credit", 1), self.row("1", "free_credit", 2)],
                 [self.row("1", "free_credit", 1), ReserveRow("2", "2026-10-29", "free_credit", 1)]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                reserve(rows, 0)


class CapitalTests(unittest.TestCase):
    def calculate(self, positions=(), **kwargs):
        args = dict(date=DAY, net_worth=1_000_000, nonallowable=100_000,
                    aggregate_liabilities=6_000_000, reserve_requirement=2_000_000,
                    eligible_deposit=1_500_000, customer_payable=5_000_000, positions=positions)
        args.update(kwargs)
        return net_capital(**args)[0]

    def test_haircuts_and_indebtedness_hand_case(self):
        positions = [Position("P1", DAY, "A", "listed_equity", 50_000),
                     Position("P2", DAY, "Fund", "qualifying_money_fund", 100_000)]
        result = self.calculate(positions)
        self.assertEqual(result.haircuts, 9500)
        self.assertEqual(result.net_capital, 890500)
        self.assertEqual(result.aggregate_indebtedness, 4_500_000)
        self.assertEqual(result.required_capital, 300000)
        self.assertEqual(result.excess_capital, 590500)

    def test_floor_and_breach(self):
        result = self.calculate(net_worth=200_000, aggregate_liabilities=0, customer_payable=0)
        self.assertEqual(result.required_capital, 250000)
        self.assertEqual(result.status, "BREACH")

    def test_issuer_concentration_aggregates_lots(self):
        positions = [Position("P1", DAY, "A", "listed_equity", 50_000),
                     Position("P2", DAY, "A", "listed_equity", 50_000)]
        with self.assertRaises(ValueError):
            self.calculate(positions)

    def test_short_and_unknown_rejected(self):
        for position in [Position("P1", DAY, "A", "listed_equity", 100, "short"),
                         Position("P1", DAY, "A", "option", 100)]:
            with self.assertRaises(ValueError):
                self.calculate([position])


class LeaseTests(unittest.TestCase):
    def test_present_value_and_finance_hand_case(self):
        lease = Lease("F", "finance", (110, 110), 0.10)
        self.assertAlmostEqual(present_value(lease.payments, .1), 190.9090909091)
        rows = schedule(lease)
        self.assertAlmostEqual(rows[0].interest, 19.0909090909)
        self.assertAlmostEqual(rows[0].closing_liability, 100)
        self.assertAlmostEqual(rows[0].rou_amortization, 95.4545454545)
        self.assertEqual(rows[-1].closing_liability, 0)
        self.assertEqual(rows[-1].closing_rou, 0)

    def test_operating_cost_with_prepaid_incentive_and_costs(self):
        rows = schedule(Lease("O", "operating", (100, 120), 0, 20, 10, 4))
        self.assertEqual(rows[0].opening_rou, 234)
        self.assertEqual([row.lease_expense for row in rows], [117, 117])
        self.assertEqual(rows[-1].closing_rou, 0)

    def test_modification_hand_case(self):
        for kind in ["operating", "finance"]:
            rows = schedule(Lease("M", kind, (100, 100, 100), 0),
                            Modification(2, (121, 121), .1))
            self.assertAlmostEqual(rows[1].remeasurement, 10)
            self.assertAlmostEqual(rows[1].interest, 21)
            self.assertAlmostEqual(rows[1].closing_liability, 110)
            self.assertEqual(rows[-1].closing_liability, 0)
            self.assertEqual(rows[-1].closing_rou, 0)
            if kind == "operating":
                self.assertAlmostEqual(rows[1].lease_expense, 121)

    def test_every_journal_balances_and_rolls_forward(self):
        for kind in ["operating", "finance"]:
            lease = Lease("L", kind, (100, 110, 120), .01, 20, 5, 3)
            rows = schedule(lease, Modification(2, (130, 140), .02))
            totals = {}
            for line in journals(lease, rows):
                totals[line.journal_id] = totals.get(line.journal_id, 0) + line.debit - line.credit
            self.assertTrue(all(abs(value) < 1e-8 for value in totals.values()))
            for row in rows:
                self.assertAlmostEqual(row.opening_liability + row.remeasurement + row.interest - row.payment,
                                       row.closing_liability)
                self.assertAlmostEqual(row.opening_rou + row.rou_adjustment - row.rou_amortization,
                                       row.closing_rou)

    def test_unsupported_modifications_and_invalid_inputs(self):
        lease = Lease("L", "operating", (100, 100), 0)
        for modification in [Modification(2, (90, 90), 0), Modification(0, (100, 100), 0),
                             Modification(2, (90,), 0, "termination")]:
            with self.assertRaises(ValueError):
                schedule(lease, modification)
        for values, rate in [((), .1), ((100,), -.1), ((float("nan"),), 0)]:
            with self.assertRaises(ValueError):
                present_value(values, rate)


class ControlTests(unittest.TestCase):
    def test_evidence_sequence_independence_and_missing(self):
        self.assertEqual(test_evidence(GOOD_EVIDENCE).result, "PASS")
        bad = replace(GOOD_EVIDENCE, reviewer="Maker", artifact_sha256="", reviewed_on="2026-11-01")
        result = test_evidence(bad)
        self.assertEqual(result.result, "FAIL")
        self.assertIn("Potential material weakness", result.deficiency_screen)
        self.assertIn("Review past due", result.exceptions)
        self.assertEqual(test_evidence(replace(GOOD_EVIDENCE, reviewed_on="")).result, "FAIL")

    def test_deficiency_screen_boundaries(self):
        self.assertEqual(deficiency(5, 5, False), "No exception")
        self.assertIn("significant", deficiency(3, 3, True))
        self.assertIn("Control deficiency", deficiency(2, 5, True))

    def test_seeded_sample_is_order_invariant(self):
        population = [replace(GOOD_EVIDENCE, evidence_id=f"E{index}") for index in range(20)]
        first = select_sample(population, 5, 42)
        self.assertEqual(first, select_sample(reversed(population), 5, 42))
        self.assertEqual(len({item.evidence_id for item in first}), 5)
        with self.assertRaises(ValueError):
            select_sample(population, 21, 42)

    def test_variance_zero_and_and_threshold(self):
        self.assertEqual(variance(100000, 0), (100000, None, True))
        self.assertFalse(variance(1_050_000, 1_000_000)[2])
        self.assertTrue(variance(1_200_000, 1_000_000)[2])


class CovenantTests(unittest.TestCase):
    def test_hand_case_and_limit_equality(self):
        item = CovenantInput("A", DAY, 4_500_000, 500_000, 0, 1_000_000, 250_000)
        result = evaluate_covenants(item, GOOD_EVIDENCE)
        self.assertEqual([row.actual for row in result], [4, 4, 500000])
        self.assertTrue(all(row.financial_status == "PASS" for row in result))
        bad_evidence = replace(GOOD_EVIDENCE, reviewer="Maker")
        self.assertEqual(evaluate_covenants(item, bad_evidence)[0].overall_status, "EVIDENCE EXCEPTION")

    def test_zero_denominators_never_pass(self):
        result = evaluate_covenants(CovenantInput("A", DAY, 100, 0, 0, 0, 0), GOOD_EVIDENCE)
        self.assertEqual([row.financial_status for row in result], ["UNAVAILABLE", "UNAVAILABLE", "BREACH"])


class VendorTests(unittest.TestCase):
    def test_weighted_score_and_calendar_hand_case(self):
        vendor = Vendor("V", "Clearing", "Risk", 5, 4, 3, "2026-07-01")
        responses = [Response("V", "security", 5, "S"), Response("V", "continuity", 5, "B"),
                     Response("V", "financial", 0, "F"), Response("V", "compliance", 5, "")]
        result = vendor_risk(vendor, responses, DAY)
        self.assertEqual(result.questionnaire_score, .6)
        self.assertAlmostEqual(result.residual_risk, 1.6)
        self.assertEqual((result.tier, result.next_review, result.review_status),
                         ("Tier 1", "2026-09-29", "OVERDUE"))
        self.assertEqual(result.missing_evidence, 1)

    def test_missing_responses_are_zero_and_duplicates_fail(self):
        vendor = Vendor("V", "Office", "Ops", 1, 1, 1, DAY)
        self.assertEqual(vendor_risk(vendor, [], DAY).questionnaire_score, 0)
        response = Response("V", "security", 5, "S")
        with self.assertRaises(ValueError):
            vendor_risk(vendor, [response, response], DAY)
