"""Replay a finished or explicitly stopped synthetic call's CUDA speech.

No hosted requests or private conversation. The source must be a completed
voice-video-soak audit with prompts matching the committed neutral fixtures.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from local_app.engine import speech_phrases
from local_app.speech_runtime import create_speech
from scripts.review_lip_sync import preview_idle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--label',required=True)
    parser.add_argument('--memory-policy',choices=['retain','shrink'],required=True)
    args=parser.parse_args()
    if not all(re.fullmatch(r'[a-z0-9-]{1,32}',v) for v in [args.source,args.label]):
        parser.error('Use bounded lowercase source and output labels.')
    preview_idle()
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.2)
    except OSError:pass
    else:connection.close();raise RuntimeError('Finish the call benchmark first.')
    audit=ROOT/'generated/local-app/audit'
    source=audit/('voice-video-soak-'+args.source)
    if not (source/'browser-done.json').is_file():raise ValueError('Finish or explicitly stop the source call first.')
    raw=(source/'qualification.json').read_bytes()
    rows=json.loads(raw)['results']
    fixtures=json.loads((ROOT/'config/video-call-qualification.json').read_text())
    prompts={r['case']:r['prompt'] for r in fixtures}
    corpus=[]
    for row in rows:
        if row.get('case') not in prompts or row.get('expected',{}).get('prompt')!=prompts[row['case']]:
            raise ValueError('Only the committed synthetic call prompts are permitted.')
        text=row.get('job',{}).get('text','')
        if text:
            if not isinstance(text,str) or len(text)>2000:raise ValueError('Invalid synthetic reply.')
            corpus.append({'case':row['case'],'cycle':row['cycle'],'text':text})
    if len(corpus)<40:raise ValueError('Replay at least forty varied call replies.')
    folder=audit/('speech-memory-'+args.label);folder.mkdir(exist_ok=False)
    import numpy as np
    import soundfile as sf
    import torch
    start=time.perf_counter()
    voice,metadata,dll=create_speech('cuda',shrink_gpu_arena=args.memory_policy=='shrink')
    result={'source':args.source,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'runtime':metadata,'load_s':time.perf_counter()-start,'rows':[],
            'scope':'Two sequential replays of synthetic call text, with a new single speech thread per reply as in the app. Speech-only stress, no renderer/ASR/network or physical audio acceptance. GPU samples include other processes.'}
    # Match the call's startup speech and fixture synthesis before varied replies.
    for text in ['Hello there.',*[r['prompt'] for r in fixtures]]:
        voice.create(text,voice='af_sarah',speed=1,lang='en-us')
    for repeat in range(2):
        for index,item in enumerate(corpus):
            preview_idle()
            record={'repeat':repeat,'index':index,**item,'phrases':[]}
            def synthesize():
                for phrase_index,text in enumerate(speech_phrases(item['text'])):
                    began=time.perf_counter()
                    try:
                        audio,rate=voice.create(text,voice='af_sarah',speed=1,lang='en-us')
                        elapsed=time.perf_counter()-began
                        if not np.isfinite(audio).all() or not .05<len(audio)/rate<30:
                            raise ValueError('Invalid speech waveform.')
                        filename=f'{repeat}-{index}-{phrase_index}.wav'
                        sf.write(folder/filename,audio,rate,subtype='PCM_16')
                        record['phrases'].append({'seconds':elapsed,'file':filename,'text':text,
                            'duration_s':len(audio)/rate,'rms':float(np.sqrt(np.mean(audio**2))),
                            'peak':float(np.max(np.abs(audio))),
                            'clipped_fraction':float(np.mean(np.abs(audio)>=.999))})
                    except Exception as error:
                        record['phrases'].append({'seconds':time.perf_counter()-began,
                            'error_type':type(error).__name__,'error':str(error)[:2000]})
                        break
            with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(synthesize).result()
            free,total=torch.cuda.mem_get_info()
            record['gpu_used_mib']=(total-free)/1048576
            result['rows'].append(record)
            (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            if index%20==0:print(json.dumps({'repeat':repeat,'index':index,'gpu_used_mib':record['gpu_used_mib']}),flush=True)
    phrases=[p for r in result['rows'] for p in r['phrases']]
    times=sorted(p['seconds'] for p in phrases if 'error' not in p)
    result['summary']={'replies':len(result['rows']),'phrases':len(phrases),
        'failures':sum('error' in p for p in phrases),
        'median_s':statistics.median(times) if times else None,
        'p95_s':times[math.ceil(len(times)*.95)-1] if times else None,
        'max_sampled_gpu_mib':max(r['gpu_used_mib'] for r in result['rows']),
        'last_sampled_gpu_mib':result['rows'][-1]['gpu_used_mib']}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary']),flush=True)
    if result['summary']['failures']:raise SystemExit(1)


if __name__=='__main__':main()
