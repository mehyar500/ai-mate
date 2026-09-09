import copy
import math
import subprocess
import sys
import unittest
from scripts.economics import calculate, load, report, price_floor, forecast, no_sales, demo_forecast, gpu_session_cost, pilot_estimate, ROOT

class EconomicsTests(unittest.TestCase):
    def test_optional_pilot_counts_credit_purchase_once_and_utilization_separately(self):
        d=pilot_estimate(load())
        self.assertAlmostEqual(d['total'],57.375)
        self.assertAlmostEqual(d['months'][0],28.925)
        self.assertAlmostEqual(d['remaining'],42.625)
        r=d['calls'][1]
        self.assertEqual((r['input_tokens'],r['output_tokens']),(240000,7200))
        self.assertAlmostEqual(r['dialogue'],.014688)
        self.assertAlmostEqual(r['gpu'],.7734375)
        self.assertAlmostEqual(r['transport'],.045)
        self.assertGreater(r['technical_half_used'],r['technical'])
        offer=d['offers'][1]
        self.assertAlmostEqual(offer['contribution'],5.1918)
        self.assertAlmostEqual(offer['margin'],offer['contribution']/9.99)

    def test_pilot_overruns_and_invalid_fee_inputs_are_visible(self):
        c=load();c['gpu_pilot']['monthly_test_hours']=720
        self.assertLess(pilot_estimate(c)['remaining'],0)
        for key,value in [('gpu_5090_hour',float('nan')),('processor_fraction_assumed',1),('idle_seconds',-1)]:
            c=load();c['gpu_pilot'][key]=value
            with self.assertRaises(ValueError):pilot_estimate(c)

    def test_gpu_call_cost_charges_startup_and_idle_once(self):
        self.assertAlmostEqual(gpu_session_cost(1.116,30),.6045)
        self.assertAlmostEqual(gpu_session_cost(1.116,60),1.1625)
        self.assertAlmostEqual(gpu_session_cost(.74,30,0,0),.37)
        self.assertGreater(gpu_session_cost(.74,30),.37)
        for values in [(True,30,60,90),(1,0,0,0),(1,30,-1,90),(math.nan,30,60,90)]:
            with self.assertRaises(ValueError):gpu_session_cost(*values)

    def test_demo_budget_includes_power_and_single_buffer(self):
        d=demo_forecast(load())
        self.assertEqual(d['months'][0]['expense'],6)
        self.assertAlmostEqual(d['months'][1]['expense'],1.8)
        self.assertAlmostEqual(d['expense'],9.6)
        self.assertAlmostEqual(d['funding'],84.6)
        self.assertEqual(d['first_demo_funding'],81)
        self.assertTrue(d['within_cap'])

    def test_demo_rate_overrun_is_visible(self):
        c=load();c['poc']['incremental_tools_monthly']=10
        d=demo_forecast(c)
        self.assertAlmostEqual(d['funding'],114.6)
        self.assertFalse(d['within_cap'])
        self.assertLess(d['headroom'],0)

    def test_demo_is_independent_of_deferred_commercial_costs(self):
        c=load();before=demo_forecast(c)
        c['assumptions'].update(registration=10000,founder_labor=5000,payers=500)
        self.assertEqual(demo_forecast(c),before)

    def test_demo_optional_spend_can_be_removed(self):
        c=load();c['poc']['incremental_tools_monthly']=10
        c['poc']['incremental_tools_monthly']=0
        self.assertAlmostEqual(demo_forecast(c)['funding'],84.6)
        c['poc']['contingency']=0
        d=demo_forecast(c)
        self.assertEqual(d['expense'],d['funding'])

    def test_demo_invalid_inputs(self):
        for key,value in [('local_kw',-1),('quarter_cap',True),('fallback_gpu_hour',math.nan)]:
            c=load();c['poc'][key]=value
            with self.assertRaises(ValueError): demo_forecast(c)
        c=load();c['poc']['months'][0]['local_hours']=-1
        with self.assertRaises(ValueError): demo_forecast(c)
        c=load();c['poc']['months']=[]
        with self.assertRaises(ValueError): demo_forecast(c)

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
        self.assertEqual(d["startup"],7020)
        self.assertEqual(d["verification"],156.25)
        c["assumptions"]["verification_per_new_user"]=0
        self.assertAlmostEqual(d["first_cost"]-calculate(c)["first_cost"],156.25)

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
        self.assertAlmostEqual(calculate(c)["first_cost"]-d["first_cost"],2000)

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
        self.assertAlmostEqual(d['funding_before_receipts'],10082)
        c['assumptions']['working_buffer']=0
        after=calculate(c)
        self.assertAlmostEqual(d['funding_before_receipts']-after['funding_before_receipts'],1500)
        self.assertEqual(d['first_profit'],after['first_profit'])

    def test_startup_profit_is_distinct_from_available_cash(self):
        c=load();c['assumptions']['payers']=420
        d=calculate(c)
        self.assertGreater(d['first_profit'],0)
        self.assertLess(d['cash_after_reserve'],0)

    def test_three_month_expense_components_and_single_startup(self):
        f=forecast(load())
        self.assertEqual([m['startup'] for m in f['months']],[7020,0,0])
        self.assertAlmostEqual(f['totals']['expenses'],11866.14)
        self.assertAlmostEqual(f['totals']['profit'],-5368.14)
        for m in f['months']:
            components=sum(m[k] for k in ('startup','fixed','aux','delivery','idle',
                'free_delivery','verification','acquisition','founder_pay','withheld'))
            self.assertAlmostEqual(m['expenses'],components)

    def test_new_cohorts_drive_verification_and_acquisition(self):
        c=load();before=forecast(c)
        self.assertEqual(before['totals']['verified'],185)
        self.assertEqual(before['months'][2]['verified'],110)
        c['assumptions']['cac']=20
        after=forecast(c)
        self.assertAlmostEqual(after['totals']['expenses']-before['totals']['expenses'],3200)
        self.assertEqual(after['months'][2]['acquisition'],2200)

    def test_settlement_and_reserve_cash_reconciliation(self):
        for lag in (0,1,2,5):
            c=load();c['launch']['settlement_lag_months']=lag
            f=forecast(c);t=f['totals']
            self.assertAlmostEqual(t['profit']-t['reserve']-t['unsettled'],t['cash_change'])
            self.assertAlmostEqual(t['cash_out'],sum(m['expenses']-m['withheld'] for m in f['months']))
            self.assertLessEqual(t['minimum_funding'],t['funding_without_receipts'])
        self.assertEqual(f['totals']['receipts'],0)

    def test_delayed_payout_not_new_revenue(self):
        f=forecast(load())
        self.assertEqual(f['months'][1]['receipts'],0)
        self.assertAlmostEqual(f['months'][2]['receipts'],1144.64)
        self.assertAlmostEqual(f['totals']['unsettled'],3433.92)
        self.assertAlmostEqual(f['totals']['minimum_funding'],10951.86)
        self.assertAlmostEqual(f['totals']['funding_without_receipts'],12096.50)

    def test_no_sales_retains_capacity_and_counts_no_payment_fees(self):
        f=forecast(no_sales(load()))
        self.assertEqual(f['totals']['revenue'],0)
        self.assertEqual(f['totals']['verified'],25)
        self.assertEqual(f['totals']['reserve'],0)
        self.assertAlmostEqual(f['totals']['expenses'],9478.25)
        self.assertAlmostEqual(f['totals']['profit'],-f['totals']['cash_out'])

    def test_buffer_and_reserve_not_expenses(self):
        c=load();before=forecast(c)
        c['assumptions'].update(working_buffer=0,reserve_fraction=0)
        after=forecast(c)
        self.assertEqual(before['totals']['expenses'],after['totals']['expenses'])
        self.assertAlmostEqual(before['totals']['funding_without_receipts']-after['totals']['funding_without_receipts'],1500)
        self.assertGreater(after['totals']['receipts'],before['totals']['receipts'])

    def test_invalid_launch_assumptions(self):
        for lag in (-1,1.5,True):
            c=load();c['launch']['settlement_lag_months']=lag
            with self.assertRaises(ValueError): forecast(c)
        c=load();c['launch']['months'][2]['new_payers']=99
        with self.assertRaises(ValueError): forecast(c)
        c=load();c['monthly_fixed_breakdown']['Coding tools and development API allowance']=0
        with self.assertRaises(ValueError): forecast(c)
        c=load();c['launch']['months']=[]
        with self.assertRaises(ValueError): forecast(c)
        c=load();c['launch']['months'].append(copy.deepcopy(c['launch']['months'][-1]))
        with self.assertRaises(ValueError): forecast(c)

    def test_cli_cannot_overwrite_report_with_overrides(self):
        before=(ROOT/"docs/ECONOMICS.md").read_bytes()
        for args in [("--write","--json"),("--write","--payers","20")]:
            r=subprocess.run([sys.executable,str(ROOT/"scripts/economics.py"),*args],capture_output=True)
            self.assertNotEqual(r.returncode,0)
        self.assertEqual(before,(ROOT/"docs/ECONOMICS.md").read_bytes())

if __name__=="__main__": unittest.main()
