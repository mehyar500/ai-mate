"""Compare Cloudflare with synthetic context through the actual dialogue adapter.

Maximum 24 dialogue or nine speech requests. No automatic retries, private
history, runtime selection, subscription changes or credentials in artifacts.
"""
import argparse
import base64
import io
import json
from pathlib import Path
import re
import socket
import sys
import threading
import time
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.engine import configure_runtime
from local_app.conversation import Conversation
from scripts.benchmark_cloud_speech import CASES as SPEECH_CASES

# September 8 list prices; https://developers.cloudflare.com/workers-ai/platform/pricing/
MODELS = {
    '@cf/qwen/qwen3-30b-a3b-fp8': (.051, .335),
    '@cf/zai-org/glm-4.7-flash': (.060, .400),
    '@cf/ibm-granite/granite-4.0-h-micro': (.017, .112),
    '@cf/meta/llama-3.1-8b-instruct-fp8-fast': (.045, .384),
    '@cf/meta/llama-3.2-3b-instruct': (.051, .335),
    # September 9: Google list price, passed through Unified Billing.
    'google/gemini-3.5-flash-lite': (.300, 2.500),
}
DEFAULT_MODELS = list(MODELS)[:3]  # Preserve the default 24-request maximum.
CASES = {
    'memory': "I'm nervous about Friday. What was I getting ready for?",
    'negated_motion': "Don't come closer. Just tell me something calming about this garden.",
    'call_message': 'Send me a message saying Good luck at your recital.',
    'unsupported_motion': 'Please do a cartwheel.',
}
SNAPSHOT = {'memory': 'My dog is named Nori.', 'visual_pose': 'near', 'turns': [
    {'user': 'I have a piano recital on Friday.', 'assistant': 'Which piece are you playing?'}]}
PRICING = 'https://developers.cloudflare.com/workers-ai/platform/pricing/'
GOOGLE_PRICING = 'https://ai.google.dev/gemini-api/docs/pricing'


def dialogue(auth, repeats, save, selected_model=None, selected_case=None):
    original = urllib.request.urlopen
    budget_reserved = 0.
    failed_models = set()
    for repeat in range(repeats):
        # Rotate order to reduce simple first-model/order bias.
        names = [selected_model] if selected_model else DEFAULT_MODELS.copy()
        offset = repeat % len(names)
        names = names[offset:] + names[:offset]
        for model in names:
            if model in failed_models:
                continue
            auth.model = model
            for case, user in CASES.items():
                if selected_case and case != selected_case:
                    continue
                row = {'kind': 'dialogue', 'model': model, 'case': case, 'repeat': repeat}

                def measured(request, **kwargs):
                    nonlocal budget_reserved
                    expected = f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/v1/chat/completions'
                    if request.full_url != expected or not request.data or len(request.data) > 30000:
                        raise ValueError('Unexpected benchmark request.')
                    body = json.loads(request.data)
                    if body['model'] != model or body['max_tokens'] > 512:
                        raise ValueError('Request exceeds benchmark model/token bounds.')
                    # Bytes plus message overhead conservatively reserve input tokens.
                    reservation = ((len(request.data) + 1000) * MODELS[model][0] + 512 * MODELS[model][1]) / 1e6
                    if budget_reserved + reservation > .10:
                        raise ValueError('Benchmark nominal price reservation exhausted.')
                    budget_reserved += reservation
                    # A repeated prompt must measure inference, not a cached
                    # Gateway response. This does not modify gateway settings.
                    request.add_header('cf-aig-skip-cache', 'true')
                    began = time.perf_counter()
                    with original(request, timeout=30) as response:
                        cache_status = response.headers.get('cf-aig-cache-status', 'unknown').upper()
                        row['gateway_cache_status'] = (cache_status if cache_status in
                            {'HIT', 'MISS', 'BYPASS', 'UNKNOWN'} else 'OTHER')
                        if cache_status == 'HIT':
                            raise ValueError('Cached response cannot qualify inference latency.')
                        first = response.read(1)
                        row['first_response_byte_s'] = round(time.perf_counter() - began, 3)
                        data = first + response.read(1_000_001)
                    row['complete_s'] = round(time.perf_counter() - began, 3)
                    if len(data) > 1_000_000:
                        raise ValueError('Response too large.')
                    result = json.loads(data)
                    usage = result.get('usage', {})
                    row['usage'] = {k: usage[k] for k in ['prompt_tokens', 'completion_tokens', 'total_tokens'] if k in usage}
                    if all(isinstance(usage.get(k), int) and usage[k] >= 0 for k in ['prompt_tokens', 'completion_tokens']):
                        row['list_price_usd'] = (usage['prompt_tokens'] * MODELS[model][0] + usage['completion_tokens'] * MODELS[model][1]) / 1e6
                    row['finish_reason'] = result.get('choices', [{}])[0].get('finish_reason')
                    return io.BytesIO(data)

                try:
                    with patch('local_app.conversation.urllib.request.urlopen', side_effect=measured):
                        plan = auth.plan(SNAPSHOT, user, 'video', 'fullbody', ['mira', 'garden', 'cafe', 'fullbody'], threading.Event())
                    row['plan'] = plan
                    checks = {'mode_kept': plan['presentation'] == 'video',
                              'scene_kept': plan['scene'] == 'fullbody', 'no_unrequested_motion': plan['action'] == 'none'}
                    if case == 'memory':
                        checks['recall'] = any(s in plan['reply'].lower() for s in ['piano', 'recital'])
                    if case == 'call_message':
                        checks['message'] = 'good luck at your recital' in plan.get('message', '').lower()
                    if case == 'unsupported_motion':
                        checks['unsupported_disclosed'] = bool(re.search(
                            r"cannot|can't|not able|unavailable|not supported", plan['reply'], re.I))
                    row['checks'] = checks
                except (RuntimeError, ValueError, OSError) as error:
                    row['error'] = type(error).__name__  # Never serialize URLs/headers/provider errors.
                    cause = error.__cause__ or error
                    if isinstance(cause, urllib.error.HTTPError):
                        row['http_status'] = cause.code
                    save(row)
                    failed_models.add(model)
                    break  # Skip remaining cases for a failed model, no retry here.
                save(row)


def speech(auth, save):
    for model in ['@cf/deepgram/aura-1', '@cf/deepgram/aura-2-en', '@cf/myshell-ai/melotts']:
        for case, prompt in SPEECH_CASES.items():
            melo = model.endswith('/melotts')
            body = {'prompt': prompt, 'lang': 'en'} if melo else {
                'text': prompt, 'speaker': 'luna', 'encoding': 'linear16', 'container': 'wav', 'sample_rate': 24000}
            row = {'kind': 'speech', 'model': model, 'case': case, 'characters': len(prompt),
                   'speaker': 'provider default' if melo else 'luna'}
            request = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/run/{model}',
                data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **auth.cf_headers})
            try:
                began = time.perf_counter()
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = response.read(4096)
                    row['first_4096_bytes_s'] = round(time.perf_counter() - began, 3)
                    data += response.read(2_000_001)
                    content_type = response.headers.get('Content-Type', '')
                row['complete_s'] = round(time.perf_counter() - began, 3)
                if len(data) > 2_000_000:
                    raise ValueError('Audio exceeds limit.')
                if 'json' in content_type:
                    result = json.loads(data)
                    result = result.get('result', result)
                    data = base64.b64decode(result['audio'], validate=True)
                # SoundFile decodes WAV/MP3 entirely in memory, no provider URL is fetched.
                import soundfile as sf
                audio, rate = sf.read(io.BytesIO(data), dtype='float32', always_2d=True)
                duration = len(audio) / rate
                if not .1 < duration <= 30 or audio.shape[1] != 1:
                    raise ValueError('Unsupported output audio.')
                stem = model.split('/')[-1]
                out = ROOT / f'generated/local-app/audit/cloud-compare-{stem}-{case}.wav'
                sf.write(out, audio, rate, subtype='PCM_16')
                row.update(audio_s=duration, sample_rate=rate, output=out.name)
                row['list_price_usd'] = duration / 60 * .0002 if melo else len(prompt) / 1000 * (.015 if stem == 'aura-1' else .03)
            except (ValueError, KeyError, OSError, RuntimeError) as error:
                row['error'] = type(error).__name__
                if isinstance(error, urllib.error.HTTPError):
                    row['http_status'] = error.code
                save(row)
                break
            save(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['dialogue', 'speech'])
    parser.add_argument('--repeats', type=int, choices=[1, 2], default=1)
    parser.add_argument('--model', choices=list(MODELS))
    parser.add_argument('--case', choices=list(CASES))
    parser.add_argument('--label', default='')
    args = parser.parse_args()
    if args.kind == 'speech' and args.repeats != 1:
        parser.error('Speech is bounded to one run per case/model.')
    if args.kind == 'speech' and (args.model or args.case):
        parser.error('Model/case selection applies to dialogue only.')
    if args.label and not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label, digits and hyphens only.')
    try:
        connection = socket.create_connection(('127.0.0.1', 8766), timeout=.2)
    except OSError:
        pass
    else:
        connection.close()
        parser.error('Finish the isolated call benchmark before starting another inference comparison.')
    from scripts.review_lip_sync import preview_idle
    preview_idle()
    configure_runtime()
    auth = Conversation('unused')
    if auth.provider != 'cloudflare':
        parser.error('Select the existing Cloudflare authentication configuration.')
    if args.model and args.model.startswith('google/'):
        from scripts.check_cloud_gateway import check
        if check(auth)['credits'] != 'positive':
            parser.error('Positive Unified Billing credit must be verified before this test.')
    folder = ROOT / 'generated/local-app/audit'
    folder.mkdir(exist_ok=True)
    suffix = '-' + args.label if args.label else ''
    target = folder / f'cloud-{args.kind}-comparison{suffix}.json'
    if target.exists():
        parser.error('Evidence already exists; choose a new --label.')
    results = []
    def save(row):
        results.append(row)
        target.write_text(json.dumps({'pricing_source': GOOGLE_PRICING if args.model and args.model.startswith('google/') else PRICING,
            'pricing_checked': '2026-09-09' if args.model and args.model.startswith('google/') else '2026-09-08',
            'scope': 'Synthetic prompts only; listed variable prices, not an invoice or end-to-end call latency.',
            'runtime_changed': False, 'results': results}, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
    if args.kind == 'dialogue':
        dialogue(auth, args.repeats, save, args.model, args.case)
    else:
        speech(auth, save)


if __name__ == '__main__':
    main()
