"""Network-free checks for bounded, uncached model comparisons."""
import io
import json
import unittest
import urllib.request
from unittest.mock import patch

from experiments import benchmark_cloud_comparison as benchmark


class SyntheticAdapter:
    account = 'synthetic-account'
    model = 'google/gemini-3.5-flash-lite'

    def __init__(self, *, max_tokens=512, endpoint=None):
        self.max_tokens = max_tokens
        self.endpoint = endpoint

    def plan(self, *args):
        request = urllib.request.Request(self.endpoint or
            f'https://api.cloudflare.com/client/v4/accounts/{self.account}/ai/v1/chat/completions',
            data=json.dumps({'model': self.model, 'max_tokens': self.max_tokens}).encode())
        with urllib.request.urlopen(request) as response:
            json.load(response)
        return {'presentation': 'video', 'scene': 'fullbody', 'action': 'none',
                'reply': 'Your piano recital is on Friday.'}


class Reply(io.BytesIO):
    def __init__(self, cache_status):
        super().__init__(json.dumps({'usage': {'prompt_tokens': 100, 'completion_tokens': 10},
                                    'choices': [{'finish_reason': 'stop'}]}).encode())
        self.headers = {'cf-aig-cache-status': cache_status}


class CloudComparisonTests(unittest.TestCase):
    def run_trial(self, adapter, response):
        rows = []
        with patch('urllib.request.urlopen', return_value=response) as network:
            benchmark.dialogue(adapter, 2, rows.append, adapter.model, 'memory')
        return rows, network

    def test_cache_hit_is_rejected_and_not_retried(self):
        rows, network = self.run_trial(SyntheticAdapter(), Reply('HIT'))
        self.assertEqual(network.call_count, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gateway_cache_status'], 'HIT')
        self.assertIn('error', rows[0])
        self.assertNotIn('complete_s', rows[0])
        self.assertNotIn('checks', rows[0])

    def test_request_disables_cache_and_records_actual_usage(self):
        rows = []
        with patch('urllib.request.urlopen', side_effect=lambda *a, **k: Reply('MISS')) as network:
            adapter = SyntheticAdapter()
            benchmark.dialogue(adapter, 1, rows.append, adapter.model, 'memory')
        headers = {k.lower(): v for k, v in network.call_args.args[0].header_items()}
        self.assertEqual(headers['cf-aig-skip-cache'], 'true')
        self.assertEqual(network.call_args.kwargs['timeout'], 30)
        self.assertTrue(all(rows[0]['checks'].values()))
        self.assertAlmostEqual(rows[0]['list_price_usd'], .000055)

    def test_foreign_endpoint_never_reaches_network(self):
        rows, network = self.run_trial(SyntheticAdapter(endpoint='https://example.invalid/'), Reply('MISS'))
        network.assert_not_called()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['error'], 'ValueError')
        self.assertNotIn('example.invalid', json.dumps(rows))

    def test_token_overrun_never_reaches_network(self):
        rows, network = self.run_trial(SyntheticAdapter(max_tokens=513), Reply('MISS'))
        network.assert_not_called()
        self.assertIn('error', rows[0])

    def test_price_reservation_stops_before_spending(self):
        adapter = SyntheticAdapter()
        with patch.dict(benchmark.MODELS, {adapter.model: (1000., 1000.)}):
            rows, network = self.run_trial(adapter, Reply('MISS'))
        network.assert_not_called()
        self.assertEqual(len(rows), 1)
        self.assertNotIn('list_price_usd', rows[0])


if __name__ == '__main__':
    unittest.main()
