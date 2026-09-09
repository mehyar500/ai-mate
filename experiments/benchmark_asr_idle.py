"""Compare idle recognition with a bounded fixed warm-up during the turn pause.

Eight fixed synthetic utterances, no hosted inference or live configuration
change. Keep the same 650ms endpoint; the warm-up starts 200ms into that pause.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--wake-policy', choices=['encoder', 'recognizer'], default='encoder')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label.')
    try:
        connection = socket.create_connection(('127.0.0.1', 8766), timeout=.2)
    except OSError:
        pass
    else:
        connection.close()
        parser.error('Finish the call benchmark before another inference experiment.')
    from scripts.review_lip_sync import preview_idle
    from local_app.engine import configure_runtime
    from local_app.models import Models
    from experiments.benchmark_call_asr import words
    preview_idle()
    folder = ROOT / 'generated/local-app/audit' / ('asr-idle-' + args.label)
    folder.mkdir(exist_ok=False)
    configure_runtime()
    os.environ['AI_MATE_ASR_DEVICE'] = 'cuda'
    os.environ['AI_MATE_TTS_DEVICE'] = 'cuda'
    os.environ['AI_MATE_ASR_PAUSE_WARM'] = '0'
    os.environ['AI_MATE_VISUAL_DECODER'] = 'tensorrt'
    model = Models()
    model.load_visual().prepare('fullbody')
    import numpy as np
    # Identical fixed-size encoder work, independent of user speech. It neither
    # decodes a transcript nor changes VAD, beam search or the encoder window.
    warm_features = np.zeros((80, 3000), dtype=np.float32)
    fixtures = ROOT / 'generated/local-app/audit/voice-video-qualification-wave-trim'
    primer_raw = (fixtures / 'greeting.wav').read_bytes()
    specs = json.loads((ROOT / 'config/video-call-qualification.json').read_text())
    expected = {row['case']: row['prompt'] for row in specs}
    cases = ['greeting', 'negated_return']
    rows = []
    for repeat in range(2):
        policies = ['none', args.wake_policy] if repeat == 0 else [args.wake_policy, 'none']
        for policy in policies:
            for case in cases:
                preview_idle()
                raw = (fixtures / (case + '.wav')).read_bytes()
                time.sleep(5)
                pause_start = time.perf_counter()
                primer_s = 0.
                if policy == 'encoder':
                    model.asr.encode(warm_features)
                    primer_s = time.perf_counter() - pause_start
                elif policy == 'recognizer':
                    model.transcribe(primer_raw)
                    primer_s = time.perf_counter() - pause_start
                # The request would arrive 450ms after the warm-up signal.
                time.sleep(max(0, .45 - (time.perf_counter() - pause_start)))
                started = time.perf_counter()
                text = model.transcribe(raw)
                row = {'repeat': repeat, 'policy': policy, 'case': case,
                       'fixture_sha256': hashlib.sha256(raw).hexdigest(),
                       'primer_s': primer_s, 'asr_s': time.perf_counter() - started,
                       'text': text, 'expected': expected[case],
                       'same_words': words(text) == words(expected[case])}
                row['endpoint_delay_s'] = max(0, primer_s - .45)
                row['ready_after_endpoint_s'] = row['asr_s'] + row['endpoint_delay_s']
                rows.append(row)
                result = {'scope': 'Five seconds idle, optional fixed encoder or recognizer warm-up, '
                          'then recognition at the unchanged endpoint. Eight synthetic '
                          'inputs; no browser, hosted dialogue, private audio or live selection.',
                          'warmup_shape': list(warm_features.shape),
                          'endpoint_remainder_s': .45, 'rows': rows}
                (folder / 'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(row), flush=True)
    for policy in ['none', args.wake_policy]:
        selected = [row for row in rows if row['policy'] == policy]
        print(json.dumps({'policy': policy, 'samples': len(selected),
                          'median_asr_s': statistics.median(row['asr_s'] for row in selected),
                          'all_same_words': all(row['same_words'] for row in selected)}), flush=True)


if __name__ == '__main__':
    main()
