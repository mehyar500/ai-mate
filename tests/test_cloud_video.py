import unittest
from unittest.mock import MagicMock

from experiments.benchmark_cloud_video import credits, response_result


class CloudVideoResponseTests(unittest.TestCase):
    def test_balance_units_cannot_inflate_available_spending_money(self):
        auth=MagicMock();auth.account='synthetic';auth.cf_headers={}
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value=b'{"success":true,"result":{"balance":910}}'
        self.assertAlmostEqual(credits(auth,opener),9.10)
        opener.open.return_value.__enter__.return_value.read.return_value=b'{"success":false,"result":{"balance":1000}}'
        with self.assertRaises(ValueError):
            credits(auth,opener)
    def test_direct_and_live_v4_envelope_preserve_playable_result(self):
        payload = {'state':'Completed', 'result':{'video':'https://example.com/video.mp4'},
                   'usage':{'seconds':5}}
        for response in [payload, {'success':True, 'result':payload}]:
            self.assertEqual(response_result(response), payload)

    def test_http_success_does_not_hide_provider_failure(self):
        payload = {'state':'Failed', 'error':'Provider unavailable'}
        self.assertEqual(response_result({'success':True,'result':payload}),payload)
        self.assertEqual(response_result({'success':False,'result':{'video':'bad'},'errors':['Denied']})['state'],'Failed')

    def test_unknown_schema_is_not_reported_as_completed(self):
        self.assertEqual(response_result({'result':{'request_id':'opaque'}})['state'],'unknown')
        with self.assertRaises(ValueError):
            response_result([])

    def test_plain_video_result_is_preserved(self):
        result=response_result({'success':True,'result':{'video':'https://example.com/video.mp4'}})
        self.assertEqual(result['result']['video'],'https://example.com/video.mp4')
