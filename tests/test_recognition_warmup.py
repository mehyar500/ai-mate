"""Resource bounds and failure isolation for optional fixed-audio preparation."""
import threading
import unittest

from local_app.models import RecognitionWarmup, pause_warm_enabled


class RecognitionWarmupTests(unittest.TestCase):
    def test_explicit_flag_only(self):
        self.assertFalse(pause_warm_enabled({}))
        self.assertFalse(pause_warm_enabled({'AI_MATE_ASR_PAUSE_WARM': '0'}))
        self.assertTrue(pause_warm_enabled({'AI_MATE_ASR_PAUSE_WARM': '1'}))
        for value in ['', 'yes', 'true', '2']:
            with self.assertRaises(ValueError):
                pause_warm_enabled({'AI_MATE_ASR_PAUSE_WARM': value})

    def test_at_most_one_pending_warmup_and_cooldown(self):
        entered, release = threading.Event(), threading.Event()
        clock, calls = [10.], []
        def prepare():
            calls.append(True)
            entered.set()
            release.wait(2)
        warm = RecognitionWarmup(prepare, now=lambda: clock[0])
        try:
            self.assertIsNone(warm.finish())
            self.assertTrue(warm.request())
            self.assertTrue(entered.wait(1))
            clock[0] = 15.
            self.assertFalse(warm.request())  # No queue even after cooldown.
            release.set()
            result = warm.finish()
            self.assertTrue(result['ok'])
            self.assertEqual(len(calls), 1)
            self.assertIsNone(warm.finish())
            self.assertTrue(warm.request())
            self.assertTrue(warm.finish()['ok'])
            self.assertFalse(warm.request())
            clock[0] = 17.
            self.assertTrue(warm.request())
            self.assertTrue(warm.finish()['ok'])
        finally:
            release.set()
            warm.close()
        self.assertFalse(warm.request())

    def test_failure_disables_optimization_without_exposing_details(self):
        def fail():
            raise ValueError('Synthetic private details must not escape.')
        warm = RecognitionWarmup(fail)
        try:
            self.assertTrue(warm.request())
            result = warm.finish()
            self.assertFalse(result['ok'])
            self.assertEqual(result['error_type'], 'ValueError')
            self.assertNotIn('private', str(result))
            self.assertFalse(warm.request())
        finally:
            warm.close()
