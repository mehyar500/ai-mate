import copy
import math
import subprocess
import sys
import unittest
from scripts.economics import calculate, load, report, ROOT


class EconomicsTests(unittest.TestCase):
    def test_gpu_idle_and_sfu_units(self):
        d = calculate(load())
        self.assertAlmostEqual(d["gpu_per_minute"], 1.2 / 60 / 0.5)
        self.assertAlmostEqual(d["media_per_minute"], 1.128 * 1e6 * 60 / 8 / 1e9 * 0.05)

    def test_full_prompt_is_billed_each_turn(self):
        d = calculate(load())
        self.assertAlmostEqual(d["managed_llm_per_minute"], (3 * 4096 * .051 + 100 * .335) / 1e6)

    def test_reserve_changes_cash_not_contribution(self):
        c = load()
        baseline = calculate(c)
        c["assumptions_not_vendor_quotes"]["reserve_fraction"] = 0
        after = calculate(c)
        self.assertEqual(baseline["cohort_surplus"], after["cohort_surplus"])
        self.assertAlmostEqual(after["cohort_cash_before_age_and_tax"] - baseline["cohort_cash_before_age_and_tax"], baseline["cohort_gross"] * .1)

    def test_low_utilization_can_make_sales_loss_making(self):
        c = load()
        c["assumptions_not_vendor_quotes"]["billable_utilization"] = .1
        d = calculate(c)
        self.assertLess(d["plans"][1]["contribution"], 0)
        self.assertLess(d["cohort_surplus"], 0)

    def test_failed_clips_cost_money(self):
        c = load()
        baseline = calculate(c)
        c["assumptions_not_vendor_quotes"]["clip_success_fraction"] = 1
        self.assertLess(calculate(c)["clip_cost"], baseline["clip_cost"])

    def test_invalid_cost_inputs_rejected(self):
        for key, value in (("billable_utilization", 0), ("billable_utilization", 1.1), ("clip_success_fraction", 0), ("gpu_per_hour", -1), ("gpu_per_hour", math.nan), ("reserve_fraction", 2), ("concurrent_calls_per_gpu", 0)):
            with self.subTest(key=key, value=value):
                c = copy.deepcopy(load())
                c["assumptions_not_vendor_quotes"][key] = value
                with self.assertRaises(ValueError):
                    calculate(c)

    def test_checked_in_report_matches_config(self):
        self.assertEqual((ROOT / "docs/product/ECONOMICS.md").read_text(encoding="utf-8"), report(load()))

    def test_changed_assumptions_update_report_narrative(self):
        c = load()
        a = c["assumptions_not_vendor_quotes"]
        a["call_turns_per_minute"] = 1
        a["gpu_per_hour"] = 2
        a["billable_utilization"] = .25
        a["processor_fraction"] = .2
        a["clips_per_pack"] = 7
        result = report(c)
        self.assertIn("122,880 input + 3,000 output", result)
        self.assertIn("245,760 + 6,000", result)
        self.assertNotIn("368,640", result)
        self.assertIn("($2.00 GPU + $0.20 VM extras)", result)
        self.assertIn("25% utilization", result)
        self.assertIn("20% + $0.50/payment", result)
        self.assertIn("$9.99/7 delivered videos", result)

    def test_free_and_paid_age_checks_are_counted(self):
        c = load()
        self.assertEqual(calculate(c)["cohort_first_month_age_cost"], 600)
        c["assumptions_not_vendor_quotes"]["cohort_new_free_users"] = 0
        self.assertEqual(calculate(c)["cohort_first_month_age_cost"], 100)

    def test_chaturbate_buyer_and_performer_are_distinct(self):
        result = report(load())
        self.assertIn("| 30 | $2.40 | $1.50 | $72.00 / $144.00 | $45.00 / $90.00 |", result)

    def test_report_supports_one_plan(self):
        c = load()
        c["plans"] = [dict(c["plans"][0], share=1)]
        self.assertNotIn("Together contribution", report(c))

    def test_json_cannot_overwrite_markdown(self):
        before = (ROOT / "docs/product/ECONOMICS.md").read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/economics.py"), "--write", "--json"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, (ROOT / "docs/product/ECONOMICS.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
