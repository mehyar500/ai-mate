"""Local signal/ASR review and same-text Kokoro baseline; no network or history.

Recognition is an intelligibility proxy, not a human voice-quality rating.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_cloud_speech import CASES


def main():
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from faster_whisper import WhisperModel
    from kokoro_onnx import Kokoro
    folder = ROOT / 'generated/local-app/audit'
    cache = ROOT / '.cache/local-poc'
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(cache / 'kokoro-v1.0.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    voice = Kokoro.from_session(session, str(cache / 'voices-v1.0.bin'))
    asr = WhisperModel(str(cache / 'asr-base-en'), device='cpu', compute_type='int8',
                       cpu_threads=4, num_workers=1, local_files_only=True)
    voice.create('Hello there.', voice='af_sarah', speed=1, lang='en-us')
    rows = []
    for model in ['kokoro', 'aura-1', 'aura-2-en', 'melotts']:
        for case, text in CASES.items():
            path = folder / f'cloud-compare-{model}-{case}.wav'
            row = {'model': model, 'case': case, 'expected': text}
            if model == 'kokoro':
                began = time.perf_counter()
                audio, rate = voice.create(text, voice='af_sarah', speed=1, lang='en-us')
                row['complete_s'] = round(time.perf_counter() - began, 3)
                sf.write(path, audio, rate, subtype='PCM_16')
            if not path.is_file():
                row['error'] = 'Missing benchmark audio'
                rows.append(row)
                continue
            audio, rate = sf.read(path, dtype='float32')
            if audio.ndim != 1 or not .1 < len(audio) / rate <= 30:
                raise ValueError('Unexpected benchmark WAV.')
            row.update(audio_s=len(audio) / rate, rms=float(np.sqrt(np.mean(audio ** 2))),
                       peak=float(np.max(np.abs(audio))), clipped_fraction=float(np.mean(np.abs(audio) >= .999)))
            segments, _ = asr.transcribe(str(path), language='en', beam_size=1, vad_filter=True, condition_on_previous_text=False)
            row['transcribed'] = ' '.join(s.text.strip() for s in segments)
            rows.append(row)
            print(json.dumps(row), flush=True)
    result = {'scope': 'Synthetic WAV signal and Whisper Base English ASR review; no physical speaker or subjective MOS test.',
              'kokoro': 'ONNX float32, af_sarah, CPU four threads, one warm-up utterance', 'rows': rows}
    (folder / 'cloud-speech-quality.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
