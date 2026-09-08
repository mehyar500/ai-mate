"""Review only isolated phrase benchmark outputs; never the live conversation."""
import hashlib
import json
from pathlib import Path
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
import soundfile as sf
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'generated/local-app/audit'


def main():
    asr = WhisperModel(str(ROOT/'.cache/local-poc/asr-base-en'), device='cpu', compute_type='int8',
                       cpu_threads=4, num_workers=1, local_files_only=True)
    results = []
    for label in ['whole', 'phrases', 'phrases-b16', 'phrases-approach']:
        folder = AUDIT/('speech-'+label)
        if not (folder/'engine-results.json').exists():
            continue
        job = json.loads((folder/'engine-results.json').read_text())[-1]
        if job['state'] != 'done':
            raise ValueError('Benchmark did not complete.')
        browser = json.loads((folder/'browser-results.json').read_text())
        waves = []; rate = None; frames = []; hashes = []
        for chunk in job['chunks']:
            name = chunk['audio'].rsplit('/', 1)[-1]
            if not re.fullmatch(r'[a-f0-9]{32}-\d+\.wav', name):
                raise ValueError('Unexpected synthetic media path.')
            audio, current_rate = sf.read(folder/name, dtype='float32')
            if rate is not None and current_rate != rate:
                raise ValueError('Sample rates differ.')
            rate = current_rate; waves.append(audio)
            video = (folder/name).with_suffix('.mp4')
            hashes.append(hashlib.sha256(video.read_bytes()).hexdigest())
            capture = cv2.VideoCapture(str(video)); decoded = []
            try:
                for _ in range(601):
                    ok, frame = capture.read()
                    if not ok: break
                    decoded.append(frame)
                if not decoded or len(decoded) > 600:
                    raise ValueError('Unexpected clip length.')
            finally:
                capture.release()
            for offset in [0, len(decoded)//2, len(decoded)-1]:
                frames.append((decoded[offset], f"Part {chunk['index']+1} frame {offset}"))
        combined = np.concatenate(waves)
        audio_file = folder/'complete-speech.wav'
        sf.write(audio_file, combined, rate, subtype='PCM_16')
        segments, _ = asr.transcribe(str(audio_file), language='en', beam_size=1, condition_on_previous_text=False)
        recovered = ' '.join(s.text.strip() for s in segments)
        sheet = Image.new('RGB', (768, 410*((len(frames)+2)//3)), '#181818')
        for i, (frame, caption) in enumerate(frames):
            pic = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)); pic.thumbnail((256,384))
            x,y = i%3*256, i//3*410
            sheet.paste(pic, (x,y)); ImageDraw.Draw(sheet).text((x+4,y+386), caption, fill='white')
        sheet.save(folder/'speech-contact.jpg')
        events = browser['events']; ends = [e['at'] for e in events if e['id']=='video' and e['type']=='ended']
        starts = [e['at'] for e in events if e['id']=='video' and e['type']=='playing' and e['currentTime']<.1]
        gaps = [max(0, start-end) for start,end in zip(starts[1:],ends)]
        row = {'label':label, 'metrics':browser['metrics'], 'speech_seconds':len(combined)/rate,
               'parts':len(job['chunks']), 'video_gaps_s':gaps,
               'audio_transcribed':recovered, 'video_sha256':hashes,
               'scope':'Synthetic ASR/planner; real CPU TTS, GPU renderer, HTTP/MSE and browser audio. No physical speaker test.'}
        results.append(row)
    (AUDIT/'speech-pipeline-review.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__ == '__main__': main()
