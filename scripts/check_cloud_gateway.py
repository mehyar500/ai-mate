"""Read Unified Billing readiness using existing Cloudflare credentials.

One GET, no retries, inference, purchases, account changes or conversation reads.
Only whitelisted status fields leave this process; no balances/card details.
"""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        # Never forward account authentication to another URL.
        return None


def credit_status(data):
    if not isinstance(data, dict) or data.get('success') is not True:
        return 'unknown'
    result = data.get('result')
    balance = result.get('balance') if isinstance(result, dict) else None
    if type(balance) not in (int, float) or not math.isfinite(balance):
        return 'unknown'
    return 'positive' if balance > 0 else 'not_positive'


def check(auth):
    row = {'checked_at': datetime.now(timezone.utc).isoformat(),
           'operation': 'GET ai-gateway/billing/credit-balance',
           'auth_mode': 'key_email' if 'X-Auth-Key' in auth.cf_headers else 'token',
           'credits': 'unknown', 'inference_tested': False, 'account_modified': False}
    request = urllib.request.Request(
        f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai-gateway/billing/credit-balance',
        headers=auth.cf_headers, method='GET')
    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(request, timeout=15) as response:
            row['http_status'] = response.status
            raw = response.read(100_001)
        if len(raw) > 100_000:
            row['error'] = 'response_too_large'
        else:
            row['credits'] = credit_status(json.loads(raw))
    except urllib.error.HTTPError as error:
        row['http_status'] = error.code
        row['error'] = 'http_error'  # No provider response/body/URL in output.
    except (OSError, ValueError):
        row['error'] = 'request_or_response_error'
    return row


def main():
    from local_app.engine import configure_runtime
    from local_app.conversation import Conversation
    try:
        configure_runtime()
        auth = Conversation('unused')
        if auth.provider != 'cloudflare':
            raise ValueError('Cloudflare required')
        row = check(auth)
    except (OSError, ValueError):
        print(json.dumps({'error': 'cloudflare_configuration_unavailable', 'account_modified': False}))
        return 1
    target = ROOT / 'generated/local-app/audit/cloud-gateway-readiness.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(row))
    return 0 if row['credits'] != 'unknown' else 1


if __name__ == '__main__':
    sys.exit(main())
