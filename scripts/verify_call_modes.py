"""Exercise real local ASR -> video with synthetic speech; never reset user history.

Run against an idle server. Adds one clearly specified synthetic wave turn.
Microphone device capture and physical speaker output are separate browser checks.
"""
import io
import json
from pathlib import Path
import sys
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    base = 'http://127.0.0.1:8765'
    with urllib.request.urlopen(base+'/api/bootstrap', timeout=5) as response:
        state = json.load(response)
    if not state['ready'] or state['busy']:
        raise SystemExit('Wait for the idle ready server.')
    token = state['token']

    def request(path, body=None, audio=False):
        headers = {'X-Local-Token': token, 'Content-Type': 'audio/wav' if audio else 'application/json',
                   'X-Reply-Mode': 'video', 'X-Scene': 'auto'}
        data = body if audio or body is None else json.dumps(body).encode()
        with urllib.request.urlopen(urllib.request.Request(base+path, data=data, headers=headers), timeout=10) as response:
            return json.load(response)

    def finish(key):
        deadline = time.monotonic()+100
        while time.monotonic() < deadline:
            job = request('/api/jobs/'+key)
            if job['state'] in {'done','failed','cancelled'}:
                return job
            time.sleep(.1)
        request('/api/cancel', {'id':key})
        raise RuntimeError('Audio test exceeded 100 seconds and was cancelled.')

    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(bytes(48000))
    quiet = finish(request('/api/audio', out.getvalue(), audio=True)['id'])
    assert quiet['state']=='failed' and quiet.get('error_code')=='no_speech'
    after_quiet=request('/api/status')
    assert after_quiet['turns']==state['turns'], 'Silence changed conversation'

    # CPU-only synthesis of known test words, not the user's voice.
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    import soundfile as sf
    options=ort.SessionOptions(); options.intra_op_num_threads=4; options.inter_op_num_threads=1
    session=ort.InferenceSession(str(ROOT/'.cache/local-poc/kokoro-v1.0.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    tts=Kokoro.from_session(session,str(ROOT/'.cache/local-poc/voices-v1.0.bin'))
    samples, rate=tts.create('Wave hello and say hi briefly.',voice='af_sarah',speed=1,lang='en-us')
    raw=io.BytesIO(); sf.write(raw,samples,rate,format='WAV',subtype='PCM_16')
    started=time.perf_counter()
    job=finish(request('/api/audio',raw.getvalue(),audio=True)['id'])
    assert job['state']=='done', job.get('error')
    assert job['presentation']=='video' and job['action']=='wave'
    assert job['chunks'] and all(c.get('video') and c.get('audio') for c in job['chunks'])
    evidence={'input':'Kokoro synthetic wave command; not a microphone recording','silence_rejected':True,
              'silence_preserves_conversation':True,'job_id':job['id'],'transcript':job['user'],
              'state':job['state'],'presentation':job['presentation'],'action':job['action'],
              'metrics':job['metrics'],'render':job['chunks'][0].get('render'),
              'wall_s':round(time.perf_counter()-started,3),'physical_microphone_to_speaker_test':False}
    destination=ROOT/'generated/local-app/audit/call-modes-asr.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
