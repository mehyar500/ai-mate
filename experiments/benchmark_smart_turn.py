"""Isolated CPU end-of-turn experiment; does not change the browser or server.

Complete synthetic qualification prompts and cut prefixes probe the model, but
cannot establish real speaker accuracy. Downloads use pinned public artifacts.
Run only after active call timing has finished to avoid CPU contention.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import statistics
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/smart-turn-benchmark.json'


def download(spec, folder):
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/spec['filename']
    if not target.exists():
        url=f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{spec['filename']}"
        with urllib.request.urlopen(url,timeout=60) as response:
            payload=response.read(spec['bytes']+1)
        if len(payload)!=spec['bytes'] or hashlib.sha256(payload).hexdigest()!=spec['sha256']:
            raise ValueError('Downloaded model size or hash differs from the pin.')
        target.write_bytes(payload)
    if target.stat().st_size!=spec['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest()!=spec['sha256']:
        raise ValueError('Local model size or hash differs from the pin.')
    notice=folder/'LICENSE'
    if not notice.exists():
        url=f"https://raw.githubusercontent.com/pipecat-ai/smart-turn/{spec['source_revision']}/LICENSE"
        with urllib.request.urlopen(url,timeout=30) as response:
            license_text=response.read(16385)
        if len(license_text)>16384 or b'BSD 2-Clause License' not in license_text:
            raise ValueError('Unexpected source license response.')
        notice.write_bytes(license_text)
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-only',action='store_true')
    parser.add_argument('--label',default='v32')
    parser.add_argument('--threads',type=int,choices=[1,2,4],default=2)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    spec=json.loads(CONFIG.read_text(encoding='utf-8'))
    model=download(spec,ROOT/'.cache/local-poc/smart-turn')
    if args.download_only:
        print(json.dumps({'verified_model':spec['filename'],'bytes':model.stat().st_size,'selected_in_app':False}))
        return
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.25)
    except OSError:pass
    else:
        connection.close();raise RuntimeError('Finish the active call benchmark before CPU timing.')
    folder=ROOT/'generated/local-app/audit'/('smart-turn-'+args.label)
    folder.mkdir(exist_ok=False)
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    import torch
    from scipy.signal import resample_poly
    from transformers import WhisperFeatureExtractor
    from math import gcd
    torch.set_num_threads(args.threads)
    options=ort.SessionOptions()
    options.intra_op_num_threads=args.threads; options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    started=time.perf_counter()
    session=ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
    extractor=WhisperFeatureExtractor(chunk_length=8)
    load_s=time.perf_counter()-started
    def predict(audio):
        started=time.perf_counter()
        audio=audio[-128000:]
        if len(audio)<128000:audio=np.pad(audio,(128000-len(audio),0))
        features=extractor(audio,sampling_rate=16000,return_tensors='np',padding='max_length',
                           max_length=128000,truncation=True,do_normalize=True).input_features.astype(np.float32)
        feature_s=time.perf_counter()-started
        probability=float(session.run(None,{'input_features':features})[0].reshape(-1)[0])
        total=time.perf_counter()-started
        if not np.isfinite(probability) or not 0<=probability<=1:raise ValueError('Invalid model probability.')
        return {'probability_complete':probability,'feature_s':feature_s,'inference_s':total-feature_s,'total_s':total}
    fixtures=ROOT/'generated/local-app/audit/voice-video-qualification-temporal128'
    examples=[]
    for row in json.loads((fixtures/'fixtures.json').read_text(encoding='utf-8')):
        audio,rate=sf.read(fixtures/(row['case']+'.wav'),dtype='float32')
        if audio.ndim!=1 or not np.isfinite(audio).all():raise ValueError('Invalid synthetic audio.')
        divisor=gcd(rate,16000)
        audio=resample_poly(audio,16000//divisor,rate//divisor).astype(np.float32)
        # Match the fixture endpoint convention used by the browser harness.
        voiced=[min(i+128,len(audio)) for i in range(0,len(audio),128)
                if np.sqrt(np.mean(audio[i:i+128]**2))>.009]
        if not voiced:raise ValueError('Synthetic fixture is silent.')
        end=voiced[-1]
        examples.append((row['case'],'complete',np.pad(audio[:end],(0,3200))))
        # Prefixes are adversarial probes, not labeled real-world ground truth:
        # a prefix may itself be a valid complete thought or end inside a word.
        for fraction in [.4,.65]:
            examples.append((row['case'],f'prefix_{fraction}',np.pad(audio[:int(end*fraction)],(0,3200))))
    rows=[]
    for index,(case,kind,audio) in enumerate(examples):
        result=predict(audio)
        rows.append({'case':case,'kind':kind,'sample':index,'audio_sha256':hashlib.sha256(audio.tobytes()).hexdigest(),**result})
    timings=[row['total_s'] for row in rows[3:]]
    result={'model':spec,'threads':args.threads,'onnxruntime':ort.__version__,'torch':torch.__version__,
            'load_s':load_s,'rows':rows,'warm_timing_s':{'samples':len(timings),'median':statistics.median(timings),'p95':sorted(timings)[int(np.ceil(len(timings)*.95))-1]},
            'complete_over_half':sum(r['kind']=='complete' and r['probability_complete']>.5 for r in rows),
            'prefix_over_half':sum(r['kind']!='complete' and r['probability_complete']>.5 for r in rows),
            'scope':'Twenty complete synthesized prompts and forty cut-prefix probes, each with 200ms trailing silence. Prefixes have no human completion labels. Includes feature extraction and inference, excludes browser upload and integration. No live model selection or real-speaker accuracy claim.'}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','model']}))


if __name__=='__main__':main()
