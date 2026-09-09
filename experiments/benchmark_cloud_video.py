"""One bounded Cloudflare video trial with reviewed fictional media only.

No automatic retry, private conversation, provider key or billing modification.
Existing output prevents accidental duplicate submission. Raw media links stay local.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.engine import configure_runtime
from local_app.conversation import Conversation
from local_app.media import load_reviewed_performance
from scripts.check_cloud_gateway import NoRedirect


def response_result(data):
    """Accept documented direct output and the live Cloudflare v4 envelope."""
    if not isinstance(data, dict):
        raise ValueError('Expected an object response.')
    if data.get('success') is False:
        return {'state':'Failed', 'errors':data.get('errors', [])}
    current = data
    for _ in range(4):
        if 'state' in current:
            return current
        if isinstance(current.get('video'), str):
            return {'state':'Completed', 'result':{'video':current['video']}}
        if not isinstance(current.get('result'), dict):
            break
        current = current['result']
    return {'state':'unknown', 'error':'Unrecognized response shape',
            'shape':{k:type(v).__name__ for k,v in current.items()}}


def credits(auth, opener):
    request = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai-gateway/billing/credit-balance', headers=auth.cf_headers)
    with opener.open(request, timeout=15) as response:
        data = json.loads(response.read(100_000))
    if not isinstance(data,dict) or data.get('success') is not True or not isinstance(data.get('result'),dict):
        raise ValueError('Credit balance unavailable.')
    value = data['result'].get('balance')
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Credit balance unavailable.')
    # Live payment/balance reconciliation: 1000 units = $10, then 910 = $9.10.
    return value / 100


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=['motion-draft', 'motion-standard', 'avatar', 'ltx-smoke', 'ltx-review'])
    wrappers = parser.add_mutually_exclusive_group()
    wrappers.add_argument('--provider-envelope', action='store_true', help='Explicit diagnostic for the provider-required input wrapper.')
    wrappers.add_argument('--dual-envelope', action='store_true', help='Diagnostic: retain documented flat parameters and the provider input wrapper.')
    args = parser.parse_args()
    is_ltx = args.case.startswith('ltx-')
    if is_ltx and (args.provider_envelope or args.dual_envelope):
        parser.error('Envelope diagnostics are specific to Pruna.')
    suffix = '-dual' if args.dual_envelope else '-envelope' if args.provider_envelope else ''
    folder = ROOT/'generated/local-app/audit/cloud-video'/(args.case+suffix)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/'result.json'
    if target.exists():
        raise SystemExit('This case was already submitted. Review its result before scheduling another trial.')
    configure_runtime()
    auth = Conversation('unused')
    if auth.provider != 'cloudflare':
        raise SystemExit('Existing Cloudflare configuration is required.')
    assets = ROOT/'generated/local-app'
    if not load_reviewed_performance(assets):
        raise SystemExit('The reviewed fictional reference manifest is missing or changed.')
    source = assets/('performance-near.png' if args.case == 'avatar' else 'fullbody.png')
    picture = 'data:image/png;base64,'+base64.b64encode(source.read_bytes()).decode('ascii')
    estimate = .025 if args.case == 'motion-draft' else .10
    if is_ltx:
        model = 'lightricks/ltx-2-5-fast'
        inputs = {'prompt':'A realistic fixed-camera smartphone video of a fictional adult woman, age 30, standing in a quiet garden, fully clothed in a blue long-sleeve blouse, jeans and shoes. Her whole body stays in frame. She gently raises her right hand beside her shoulder, waves with an open palm, then lowers it while smiling and saying, "Hi, good to see you." Natural human movement. The camera stays still and the leaves barely move.',
                  'duration':5, 'resolution':'720x1280', 'fps':24, 'generate_audio':True}
        estimate = .45
    elif args.case == 'avatar':
        audio = ROOT/'generated/local-app/audit/cloud-compare-kokoro-normal.wav'
        model = 'pruna/p-video-avatar'
        inputs = {'image':picture, 'audio':'data:audio/wav;base64,'+base64.b64encode(audio.read_bytes()).decode('ascii'),
            'voice_script':'', 'voice':'Zephyr (Female)', 'voice_language':'English (US)',
            'resolution':'720p', 'video_prompt':'The fully clothed adult woman talks naturally to the camera in the quiet garden. Fixed camera, subtle facial expression.',
            'voice_prompt':'Speak naturally.', 'negative_prompt':'', 'strength_negative_prompt':.5,
            'seed':72, 'disable_safety_filter':False, 'disable_prompt_upsampling':False}
        with wave.open(str(audio), 'rb') as wav:
            estimate = .025 * wav.getnframes() / wav.getframerate()
    else:
        model = 'pruna/p-video'
        inputs = {'prompt':'A realistic fixed-camera video of the fully clothed adult woman in the reference garden. She gently raises her right hand beside her shoulder, briefly waves with an open palm, then lowers it. Keep the same face, clothing, garden and camera position. Her entire body and both shoes stay in frame. Natural human motion, almost still background, no camera zoom.',
            'image':picture, 'duration':5, 'resolution':'720p', 'fps':24, 'aspect_ratio':'2:3',
            'draft':args.case=='motion-draft', 'save_audio':False, 'seed':72,
            'prompt_upsampling':False, 'disable_safety_filter':False}
    opener = urllib.request.build_opener(NoRedirect)
    before = credits(auth, opener)
    if before < max(.25, estimate * 2):
        raise SystemExit('Insufficient credits for this bounded trial and its cost buffer.')
    row = {'case':args.case, 'model':model, 'gateway':'default', 'started_at':datetime.now(timezone.utc).isoformat(),
        'provider_envelope':args.provider_envelope,
        'dual_envelope':args.dual_envelope,
        'reference_sha256':None if is_ltx else hashlib.sha256(source.read_bytes()).hexdigest(),
        'auth_mode':'key_email' if 'X-Auth-Key' in auth.cf_headers else 'token',
        'state':'submitting', 'automatic_retries':0, 'private_history_used':False,
        'safety_filter_mode':'provider_default' if is_ltx else 'explicitly_enabled',
        'provider_list_estimate_usd':round(estimate,6),
        'cost_limit_note':'One fixed short request. Estimate is provider list pricing, not a verified Cloudflare invoice.'}
    with target.open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(row,indent=2)+'\n')
    headers = {**auth.cf_headers, 'Content-Type':'application/json', 'cf-aig-gateway-id':'default',
        'cf-aig-collect-log':'false', 'cf-aig-skip-cache':'true', 'cf-aig-max-attempts':'1',
        'cf-aig-request-timeout':'90000'}
    submitted = {**inputs, 'input':inputs} if args.dual_envelope else {'input':inputs} if args.provider_envelope else inputs
    request = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/run',
        headers=headers, data=json.dumps({'model':model,'input':submitted}).encode(), method='POST')
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=120) as response:
            row['http_status'] = response.status
            row['gateway_log_id'] = response.headers.get('cf-aig-log-id')
            raw = response.read(1_000_001)
        if len(raw)>1_000_000:
            raise ValueError('Response exceeded the bounded result size.')
        raw_data = json.loads(raw)
        row['response_keys'] = list(raw_data) if isinstance(raw_data,dict) else []
        data = response_result(raw_data)
        row['state'] = data.get('state','unknown')
        # Persist only the documented output, never authentication/request echoes.
        result = data.get('result')
        if isinstance(result,dict) and isinstance(result.get('video'),str):
            row['video_url'] = result['video']
        for field in ['error','errors','usage','gatewayMetadata','shape']:
            if field in data:
                clean = json.dumps(data[field])
                for secret in [auth.account, *auth.cf_headers.values()]:
                    if secret: clean = clean.replace(secret,'[redacted]')
                row[field] = clean[:2000]
    except urllib.error.HTTPError as error:
        row['http_status'] = error.code
        row['state'] = 'http_error'
        raw = error.read(4000).decode(errors='replace'); error.close()
        for secret in [auth.account,*auth.cf_headers.values()]:
            if secret: raw=raw.replace(secret,'[redacted]')
        row['error'] = raw[:1500]
    except (OSError, ValueError):
        row['state']='transport_or_response_error'
        row['error']='No automatic resubmission: charge/completion may be uncertain.'
    row['request_s']=round(time.perf_counter()-started,3)
    try:
        row['account_credit_delta_usd']=before-credits(auth,opener)
    except (OSError,ValueError):
        row['account_credit_delta_usd']=None
    target.write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k!='video_url'}),flush=True)


if __name__ == '__main__':
    main()
