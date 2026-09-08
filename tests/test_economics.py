import copy
import math
import subprocess
import sys
import unittest
from scripts.economics import calculate, load, report, price_floor, ROOT

class EconomicsTests(unittest.TestCase):
    def test_renderer_capacity_and_idle_allocation(self):
        d=calculate(load())
        self.assertAlmostEqual(d["renderer_minute"],.90/(60*1*.5))
        self.assertAlmostEqual(d["live_minute"],.04)
        self.assertEqual(d["idle_topup"],0)
        self.assertEqual(d["aux_fixed"],432)

    def test_no_double_counting_renderer_floor(self):
        c=load();c["assumptions"]["payers"]=20;before=calculate(c)
        c["assumptions"]["renderer_open_hours"]=0
        after=calculate(c)
        self.assertAlmostEqual(before["first_cost"]-after["first_cost"],before["idle_topup"])
        c["assumptions"]["payers"]=500
        self.assertEqual(calculate(c)["idle_topup"],0)

    def test_full_redemption_and_transaction_fees(self):
        p=calculate(load())["plans"][1]
        self.assertAlmostEqual(p["cost"],.5+.75+40*.04+40*.02+3*.15+8*.05+6*.10+29.99*.18+.5)

    def test_low_occupancy_increases_cost(self):
        c=load();before=calculate(c)
        c["assumptions"].update(streams=1,occupancy=.1)
        after=calculate(c)
        self.assertAlmostEqual(after["live_minute"],(.90/6+.0008)*1.2)
        self.assertLess(after["plans"][1]["roi"],before["plans"][1]["roi"])

    def test_500_return_impossible_with_18_percent_fees(self):
        self.assertIsNone(price_floor(1,.18,5))
        self.assertAlmostEqual(price_floor(1,.14,3),1/.11)

    def test_margin_and_return_are_distinct(self):
        for p in calculate(load())["plans"]:
            self.assertAlmostEqual(p["roi"],p["margin"]/(1-p["margin"]))
            self.assertGreater(p["margin"],.60)
            self.assertLess(p["margin"],.65)

    def test_first_month_counts_registration_and_all_age_checks(self):
        c=load();d=calculate(c)
        self.assertEqual(d["startup"],4320)
        self.assertEqual(d["verification"],12.5)
        c["assumptions"]["verification_per_new_user"]=0
        self.assertAlmostEqual(d["first_cost"]-calculate(c)["first_cost"],12.5)

    def test_paid_units_do_not_prove_first_month_profit(self):
        d=calculate(load())
        self.assertLess(d["first_profit"],0)
        self.assertGreater(d["recurring_profit"],0)
        c=load();c["assumptions"]["payers"]=500
        self.assertGreater(calculate(c)["first_profit"],0)
        self.assertLess(calculate(c)["first_roi"],3)

    def test_reserve_is_cash_not_expense(self):
        c=load();before=calculate(c)
        c["assumptions"]["reserve_fraction"]=0
        after=calculate(c)
        self.assertEqual(before["first_profit"],after["first_profit"])
        self.assertAlmostEqual(after["cash_after_reserve"]-before["cash_after_reserve"],before["revenue"]*.1)

    def test_cac_and_legal_are_counted(self):
        c=load();d=calculate(c)
        c["assumptions"].update(cac=5,legal_setup=4500)
        self.assertAlmostEqual(calculate(c)["first_cost"]-d["first_cost"],3500)

    def test_invalid_inputs(self):
        for k,v in [("streams",0),("occupancy",0),("occupancy",2),("gpu_hour",math.nan),("payers",-1),("reserve_fraction",2)]:
            with self.subTest(k=k,v=v):
                c=copy.deepcopy(load());c["assumptions"][k]=v
                with self.assertRaises(ValueError): calculate(c)

    def test_report_matches_config(self):
        self.assertEqual((ROOT/"docs/ECONOMICS.md").read_text(encoding="utf-8"),report(load()))

    def test_scene_and_proactive_media_are_budgeted(self):
        c=load();before=calculate(c)
        c['plans'][1]['scenes']+=1
        c['plans'][1]['photos']+=1
        c['plans'][1]['clips']+=1
        self.assertAlmostEqual(calculate(c)['plans'][1]['delivery']-before['plans'][1]['delivery'],.30)

    def test_internal_review_has_labor_value(self):
        d=calculate(load())
        self.assertAlmostEqual(d['verification_labor'],250)
        self.assertAlmostEqual(d['first_profit']-d['first_profit_after_review_labor'],250)

    def test_funding_counts_service_and_buffer_without_withheld_fees(self):
        c=load();d=calculate(c)
        self.assertAlmostEqual(d['funding_before_receipts'],5918.25)
        c['assumptions']['working_buffer']=0
        after=calculate(c)
        self.assertAlmostEqual(d['funding_before_receipts']-after['funding_before_receipts'],500)
        self.assertEqual(d['first_profit'],after['first_profit'])

    def test_startup_profit_is_distinct_from_available_cash(self):
        c=load();c['assumptions']['payers']=250
        d=calculate(c)
        self.assertGreater(d['first_profit'],0)
        self.assertLess(d['cash_after_reserve'],0)

    def test_cli_cannot_overwrite_report_with_overrides(self):
        before=(ROOT/"docs/ECONOMICS.md").read_bytes()
        for args in [("--write","--json"),("--write","--payers","20")]:
            r=subprocess.run([sys.executable,str(ROOT/"scripts/economics.py"),*args],capture_output=True)
            self.assertNotEqual(r.returncode,0)
        self.assertEqual(before,(ROOT/"docs/ECONOMICS.md").read_bytes())

if __name__=="__main__": unittest.main()
