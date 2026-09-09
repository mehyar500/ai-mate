"""Compare bounded CPU ASR settings on synthetic call fixtures, without cloud calls."""
import argparse
import gc
import hashlib
import io
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.models import Models


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", "").replace('\u2019', ''))


def word_errors(expected, observed):
    reference, hypothesis = words(expected), words(observed)
    previous = list(range(len(hypothesis) + 1))
    for index, word in enumerate(reference, 1):
        current = [index]
        for position, other in enumerate(hypothesis, 1):
            current.append(min(current[-1]+1, previous[position]+1,
                               previous[position-1]+(word != other)))
        previous = current
    return previous[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label, digits and hyphens only.')
    folder = ROOT/'generated/local-app/audit'/('asr-calls-'+args.label)
    folder.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from faster_whisper import WhisperModel
    from kokoro_onnx import Kokoro
    cache = ROOT/'.cache/local-poc'
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(cache/'kokoro-v1.0.onnx'), sess_options=options,
                                   providers=['CPUExecutionProvider'])
    tts = Kokoro.from_session(session, str(cache/'voices-v1.0.bin'))
    specs = json.loads((ROOT/'config/video-call-qualification.json').read_text(encoding='utf-8'))
    fixtures = []
    rng = np.random.default_rng(7309)

    def save(name, audio, rate, expected, case, condition):
        stream = io.BytesIO()
        sf.write(stream, audio, rate, format='WAV', subtype='PCM_16')
        raw = stream.getvalue()
        (folder/(name+'.wav')).write_bytes(raw)
        fixtures.append(dict(name=name, expected=expected, case=case, condition=condition,
                             duration_s=len(audio)/rate, sha256=hashlib.sha256(raw).hexdigest()))

    for voice in ['af_sarah', 'am_michael', 'bf_emma']:
        if voice not in tts.get_voices():
            raise ValueError('Benchmark voice is not installed.')
        for spec in specs:
            audio, rate = tts.create(spec['prompt'], voice=voice, speed=1,
                                     lang='en-gb' if voice.startswith('b') else 'en-us')
            save(voice+'-'+spec['case'], audio, rate, spec['prompt'], spec['case'], voice)
            if voice == 'af_sarah':
                rms = float(np.sqrt(np.mean(audio*audio)))
                noisy = np.clip(audio + rng.normal(0, rms/10**(15/20), len(audio)), -.99, .99)
                save('noise-'+spec['case'], noisy, rate, spec['prompt'], spec['case'], 'synthetic white noise 15dB SNR')
    rate = 24000
    for name, audio in [('silence', np.zeros(rate)), ('noise', rng.normal(0,.003,rate)),
                        ('tone', .05*np.sin(2*np.pi*440*np.arange(rate)/rate))]:
        save('non-speech-'+name, audio, rate, '', name, 'non-speech')
    (folder/'fixtures.json').write_text(json.dumps(fixtures, indent=2)+'\n', encoding='utf-8')
    del tts, session
    gc.collect()
    results = []
    for model, threads in [('asr-base-en',4), ('asr-base-en',8), ('asr-tiny-en',4), ('asr-tiny-en',8)]:
        started = time.perf_counter()
        adapter = Models.__new__(Models)
        adapter.asr = WhisperModel(str(cache/model), device='cpu', compute_type='int8',
            cpu_threads=threads, num_workers=1, local_files_only=True)
        loaded = time.perf_counter()-started
        adapter.transcribe((folder/(fixtures[0]['name']+'.wav')).read_bytes())
        rows = []
        for item in fixtures:
            raw = (folder/(item['name']+'.wav')).read_bytes()
            started = time.perf_counter()
            text = adapter.transcribe(raw)
            row = dict(item, text=text, seconds=time.perf_counter()-started,
                       word_errors=word_errors(item['expected'], text), words=len(words(item['expected'])))
            # A negation lost in recognition can reverse a requested action.
            if item['case'] in {'negated_return','negated_wave'}:
                row['critical_negation_kept'] = bool(set(words(text)) & {'dont','not','never'})
            rows.append(row)
        latencies = sorted(r['seconds'] for r in rows if r['expected'])
        record = dict(model=model, threads=threads, load_s=loaded, samples=len(rows),
            median_s=statistics.median(latencies), p95_s=latencies[math.ceil(len(latencies)*.95)-1],
            word_error_rate=sum(r['word_errors'] for r in rows)/sum(r['words'] for r in rows),
            critical_negation_failures=sum(r.get('critical_negation_kept') is False for r in rows),
            non_speech_hallucinations=sum(bool(r['text']) for r in rows if not r['expected']), rows=rows)
        results.append(record)
        (folder/'results.json').write_text(json.dumps({'scope':'Synthetic English voices/noise through the real WAV adapter. No physical microphone, private data, cloud call or active model switch.', 'results':results},indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in record.items() if k != 'rows'}), flush=True)
        del adapter
        gc.collect()


if __name__ == '__main__':
    main()
