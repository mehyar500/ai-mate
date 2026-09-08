import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

from scripts.check_cloud_gateway import NoRedirect, check, credit_status


class GatewayReadinessTests(unittest.TestCase):
    def test_missing_or_invalid_balance_is_unknown(self):
        for value in (None, {}, [], True, '10', float('nan'), float('inf')):
            with self.subTest(value=value):
                self.assertEqual(credit_status({'success': True, 'result': {'balance': value}}), 'unknown')
        self.assertEqual(credit_status({'success': False, 'result': {'balance': 10}}), 'unknown')

    def test_balance_status(self):
        for value, expected in ((0, 'not_positive'), (-1, 'not_positive'), (.01, 'positive')):
            self.assertEqual(credit_status({'success': True, 'result': {'balance': value}}), expected)

    def test_redirects_are_blocked(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid'))

    def test_sensitive_response_is_not_published(self):
        auth = SimpleNamespace(account='private-account', cf_headers={'X-Auth-Key': 'private-key', 'X-Auth-Email': 'private-email'})
        response = io.BytesIO(json.dumps({'success': True, 'result': {
            'balance': 123.45, 'payment_method': {'brand': 'private-card', 'last4': '6789'},
            'topup_config': {'error': 'private-error'}}}).encode())
        response.status = 200
        with patch('scripts.check_cloud_gateway.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value = response
            row = check(auth)
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(), 'GET')
            self.assertEqual(factory.return_value.open.call_count, 1)
        self.assertEqual(row['credits'], 'positive')
        published = json.dumps(row)
        for private in ('private-', '123.45', '6789'):
            self.assertNotIn(private, published)

    def test_http_failure_redacts_url_and_body_without_retry(self):
        auth = SimpleNamespace(account='private-account', cf_headers={})
        error = urllib.error.HTTPError('https://private.invalid/secret', 403, 'private-error', {}, io.BytesIO(b'private-body'))
        with patch('scripts.check_cloud_gateway.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect = error
            row = check(auth)
            self.assertEqual(factory.return_value.open.call_count, 1)
        self.assertEqual(row['credits'], 'unknown')
        self.assertEqual(row['http_status'], 403)
        self.assertNotIn('private', json.dumps(row))


if __name__ == '__main__':
    unittest.main()
