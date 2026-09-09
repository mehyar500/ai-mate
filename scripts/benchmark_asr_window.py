"""Compare shorter encoder input against the existing 30-second padded ASR.

Uses the retained 83-fixture synthetic/noise corpus and unchanged model weights.
The override is process-local; nothing is installed or selected in the app.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.models import Models
from scripts.benchmark_call_asr import words,word_errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--minimum-seconds',type=int,nargs='+',choices=[5,10,15,20],default=[10,5])
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    settings=[30,*dict.fromkeys(args.minimum_seconds)]
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.25)
    except OSError:pass
    else:
        connection.close();raise RuntimeError('Finish the active call benchmark before CPU timing.')
    folder=ROOT/'generated/local-app/audit'/('asr-window-'+args.label)
    folder.mkdir(exist_ok=False)
    import numpy as np
    import ctranslate2
    from faster_whisper import WhisperModel
    adapter=Models.__new__(Models)
    adapter.asr=WhisperModel(str(ROOT/'.cache/local-poc/asr-base-en'),device='cpu',compute_type='int8',
                             cpu_threads=8,num_workers=1,local_files_only=True)
    original=adapter.asr.encode
    setting=30; lengths=[]
    def encode(features):
        length=features.shape[-1]
        if setting<30:
            # faster-whisper pads its segment with literal zero mel columns.
            # Keep every nonzero column, at least the selected minimum duration,
            # and 0.5s of trailing padding, rounded up to a whole second.
            active=np.flatnonzero(np.any(features!=0,axis=-2))
            required=int(active[-1])+1 if len(active) else 0
            length=min(length,max(setting*100,math.ceil((required+50)/100)*100))
            features=np.ascontiguousarray(features[...,:length])
        lengths.append(length)
        if len(lengths)>32:raise RuntimeError('Experimental ASR exceeded the bounded encoder attempts.')
        return original(features)
    adapter.asr.encode=encode
    corpus=ROOT/'generated/local-app/audit/asr-calls-cpu-comparison'
    fixtures=json.loads((corpus/'fixtures.json').read_text(encoding='utf-8'))
    if len(fixtures)!=83:raise ValueError('Use the established 83-fixture corpus.')
    adapter.transcribe((corpus/(fixtures[0]['name']+'.wav')).read_bytes())
    rows=[]
    for index,item in enumerate(fixtures):
        raw=(corpus/(item['name']+'.wav')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Synthetic fixture changed.')
        for setting in (settings if index%2==0 else list(reversed(settings))):
            lengths=[];started=time.perf_counter();text=adapter.transcribe(raw)
            row={'case':item['case'],'fixture':item['name'],'minimum_seconds':setting,'seconds':time.perf_counter()-started,
                 'encoder_frames':lengths,'text':text,'expected':item['expected'],'word_errors':word_errors(item['expected'],text),
                 'word_count':len(words(item['expected'])),'sha256':item['sha256']}
            if item['case'] in {'negated_return','negated_wave'}:
                row['negation_kept']=bool(set(words(text))&{'dont','not','never'})
            rows.append(row)
        progress={'completed_fixtures':index+1,'total_fixtures':len(fixtures),'last_fixture':item['name']}
        (folder/'progress.json').write_text(json.dumps(progress)+'\n')
        if (index+1)%10==0:print(json.dumps(progress),flush=True)
    summaries=[]
    for minimum in settings:
        subset=[r for r in rows if r['minimum_seconds']==minimum]
        times=sorted(r['seconds'] for r in subset if r['expected'])
        summaries.append({'minimum_seconds':minimum,'samples':len(subset),'median_s':statistics.median(times),
                          'p95_s':times[math.ceil(len(times)*.95)-1],
                          'word_error_rate':sum(r['word_errors'] for r in subset)/sum(r['word_count'] for r in subset),
                          'negation_failures':sum(r.get('negation_kept') is False for r in subset),
                          'non_speech_hallucinations':sum(bool(r['text']) for r in subset if not r['expected'])})
    result={'model':'asr-base-en','ctranslate2':ctranslate2.__version__,'threads':8,'summaries':summaries,'rows':rows,
            'scope':'Alternating per-fixture settings with the same CPU model, WAV adapter, VAD and decoding options. Short input is an experimental change to acoustic context, not equivalent inference. Requires accuracy and integrated call checks before any selection.'}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summaries))


if __name__=='__main__':main()
