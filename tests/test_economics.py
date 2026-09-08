import copy
import math
import subprocess
import sys
import unittest
from scripts.economics import calculate, load, report, price_floor, ROOT


class EconomicsTests(unittest.TestCase):
    def test_video_seconds_and_retry_cost(self):
        c = load()
        d = calculate(c)
        self.assertAlmostEqual(d['video_formula_cost'], .125)
        self.assertAlmostEqual(d['video_budget'], .15)
        c['assumptions']['video_accepted_fraction'] = .4
        self.assertGreater(calculate(c)['video_budget'], d['video_budget'])

    def test_warm_compute_is_billed_only_on_custom_route(self):
        c = load()
        before = calculate(c)
        c['assumptions']['custom_keepwarm_seconds'] = 600
        after = calculate(c)
        self.assertGreater(after['custom_video_cost'], before['custom_video_cost'])
        self.assertEqual(after['video_budget'], before['video_budget'])

    def test_full_allowances_and_payment_fees(self):
        d = calculate(load())
        self.assertAlmostEqual(d['plans'][1]['total'], .60 + .25 + 20*.05 + 5*.15 + 19.99*.05 + .30)
        self.assertAlmostEqual(d['addons'][1]['cost'], 30*.05 + .1 + 14.99*.05 + .30)

    def test_return_is_not_margin(self):
        self.assertAlmostEqual(price_floor(1, .05), 5)
        self.assertIsNone(price_floor(1, .25))
        for p in calculate(load())['plans']:
            self.assertAlmostEqual(p['return_on_cost'], p['margin']/(1-p['margin']))

    def test_first_month_scenarios(self):
        c = load()
        for n, profitable, target in [(20, False, False), (100, True, False), (600, True, True)]:
            c['assumptions']['cohort_payers'] = n
            d = calculate(c)
            self.assertEqual(d['first_profit'] > 0, profitable)
            self.assertEqual(d['first_return'] >= 3, target)

    def test_target_threshold(self):
        c = load()
        n = calculate(c)['target_payers']
        c['assumptions']['cohort_payers'] = n
        self.assertGreaterEqual(calculate(c)['first_return'], 3)
        c['assumptions']['cohort_payers'] = n-1
        self.assertLess(calculate(c)['first_return'], 3)

    def test_acquisition_can_prevent_target(self):
        c = load()
        c['assumptions']['customer_acquisition_cost'] = 5
        self.assertIsNone(calculate(c)['target_payers'])

    def test_verification_counts_free_and_paid(self):
        c = load()
        before = calculate(c)
        c['assumptions']['new_user_verification_cost'] = 1
        self.assertAlmostEqual(calculate(c)['first_cost'] - before['first_cost'], 300)

    def test_reserve_changes_cash_not_profit(self):
        c = load()
        before = calculate(c)
        c['assumptions']['reserve_fraction'] = 0
        after = calculate(c)
        self.assertEqual(before['first_profit'], after['first_profit'])
        self.assertAlmostEqual(after['cash_after_reserve']-before['cash_after_reserve'], before['revenue']*.1)

    def test_invalid_inputs(self):
        for key, value in [('video_accepted_fraction', 0), ('video_accepted_fraction', 2), ('cohort_payers', -1), ('phone_call_minute', math.nan), ('reserve_fraction', 2)]:
            c = copy.deepcopy(load())
            c['assumptions'][key] = value
            with self.assertRaises(ValueError):
                calculate(c)

    def test_report_matches_config(self):
        self.assertEqual((ROOT/'docs/ECONOMICS.md').read_text(encoding='utf-8'), report(load()))

    def test_json_cannot_overwrite_report(self):
        before = (ROOT/'docs/ECONOMICS.md').read_bytes()
        result = subprocess.run([sys.executable, str(ROOT/'scripts/economics.py'), '--write', '--json'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, (ROOT/'docs/ECONOMICS.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
