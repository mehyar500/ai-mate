"""Compare unchanged Kokoro weights on CPU/GPU using only neutral fixed text.

Optional GPU runtime is isolated under .cache/ort-gpu-deps. Nothing selects a
new live voice, reads private memory, or calls a hosted provider.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.benchmark_supertonic import CASES
from experiments.benchmark_call_asr import words,word_errors
from scripts.review_lip_sync import preview_idle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--device',choices=['cpu','cuda'],required=True)
    parser.add_argument('--runtime',choices=['installed','isolated'],default='installed')
    parser.add_argument('--repeats',type=int,choices=[1,4],default=4)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a bounded lowercase label.')
    if args.device=='cuda' and args.runtime!='isolated':parser.error('GPU tests require the isolated runtime.')
    preview_idle()
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.2)
    except OSError:pass
    else:connection.close();raise RuntimeError('Finish the call benchmark first.')
    folder=ROOT/'generated/local-app/audit'/('speech-device-'+args.label);folder.mkdir(exist_ok=False)
    if args.runtime=='isolated':
        runtime=ROOT/'.cache/ort-gpu-deps'
        if not (runtime/'onnxruntime/__init__.py').is_file():raise RuntimeError('Install pinned isolated GPU runtime first.')
        sys.path.insert(0,str(runtime))
    import numpy as np
    import soundfile as sf
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    provider_options={'gpu_mem_limit':2*1024**3,'arena_extend_strategy':'kSameAsRequested',
                      'cudnn_conv_algo_search':'HEURISTIC','cudnn_conv_use_max_workspace':0,'use_tf32':0}
    if args.device=='cuda':
        import torch
        dll=os.add_dll_directory(str(Path(torch.__file__).parent/'lib')) if os.name=='nt' else None
        ort.preload_dlls(directory=str(Path(torch.__file__).parent/'lib'))
        if 'CUDAExecutionProvider' not in ort.get_available_providers():raise RuntimeError('CUDA provider is unavailable.')
    options=ort.SessionOptions();options.intra_op_num_threads=8;options.inter_op_num_threads=1
    providers=[('CUDAExecutionProvider',provider_options),'CPUExecutionProvider'] if args.device=='cuda' else ['CPUExecutionProvider']
    cache=ROOT/'.cache/local-poc';began=time.perf_counter()
    session=ort.InferenceSession(str(cache/'kokoro-v1.0.onnx'),sess_options=options,providers=providers)
    if session.get_providers()[0]!=('CUDAExecutionProvider' if args.device=='cuda' else 'CPUExecutionProvider'):
        raise RuntimeError('Requested speech execution provider was not activated.')
    voice=Kokoro.from_session(session,str(cache/'voices-v1.0.bin'))
    result={'runtime':args.runtime,'onnxruntime':ort.__version__,'device':args.device,'providers':session.get_providers(),
        'load_s':time.perf_counter()-began,'cpu_threads':8,'provider_options':provider_options if args.device=='cuda' else {},'rows':[],
        'scope':'Fixed neutral af_sarah text, unchanged Kokoro82M float32 weights. Warm complete-wave synthesis, includes tokenization and CPU/GPU transfers. Readback follows timing; no call, physical audio or perceptual acceptance.'}
    began=time.perf_counter();voice.create('Hello there.',voice='af_sarah',speed=1,lang='en-us');result['cold_warmup_s']=time.perf_counter()-began
    print(json.dumps({k:v for k,v in result.items() if k not in {'rows','scope'}}),flush=True)
    for repeat in range(args.repeats):
        for case,text in CASES.items():
            preview_idle()
            began=time.perf_counter();audio,rate=voice.create(text,voice='af_sarah',speed=1,lang='en-us');elapsed=time.perf_counter()-began
            if not np.isfinite(audio).all() or not .1<len(audio)/rate<30:raise ValueError('Invalid speech output.')
            target=folder/f'{case}-{repeat}.wav';sf.write(target,audio,rate,subtype='PCM_16')
            row={'case':case,'repeat':repeat,'expected':text,'seconds':elapsed,'duration_s':len(audio)/rate,'rate':rate,
                 'rms':float(np.sqrt(np.mean(audio**2))),'peak':float(np.max(np.abs(audio))),
                 'clipped_fraction':float(np.mean(np.abs(audio)>=.999)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
            result['rows'].append(row);print(json.dumps({'case':case,'seconds':elapsed,'duration_s':row['duration_s']}),flush=True)
    # Release TTS before the CPU readback. Device work never overlaps readback.
    del voice,session
    from faster_whisper import WhisperModel
    from local_app.models import Models
    adapter=Models.__new__(Models);adapter.asr=WhisperModel(str(cache/'asr-base-en'),device='cpu',compute_type='int8',cpu_threads=8,num_workers=1,local_files_only=True)
    for row in result['rows']:
        row['transcript']=adapter.transcribe((folder/f"{row['case']}-{row['repeat']}.wav").read_bytes())
        row['word_errors']=word_errors(row['expected'],row['transcript']);row['expected_words']=len(words(row['expected']))
        if row['case']=='long':row['readback_count_complete']=[int(n) for n in re.findall(r'\b\d+\b',row['transcript'])]==list(range(1,26))
    times=sorted(row['seconds'] for row in result['rows'])
    result['summary']={'samples':len(times),'median_s':statistics.median(times),'p95_s':times[math.ceil(len(times)*.95)-1],
        'by_case_median_s':{case:statistics.median(r['seconds'] for r in result['rows'] if r['case']==case) for case in CASES},
        'readback_word_errors':sum(r['word_errors'] for r in result['rows']),
        'non_count_word_errors':sum(r['word_errors'] for r in result['rows'] if r['case']!='long'),
        'complete_count_repeats':sum(r.get('readback_count_complete',False) for r in result['rows'])}
    result['model_sha256']=hashlib.sha256((cache/'kokoro-v1.0.onnx').read_bytes()).hexdigest()
    result['voices_sha256']=hashlib.sha256((cache/'voices-v1.0.bin').read_bytes()).hexdigest()
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result['summary']),flush=True)


if __name__=='__main__':main()
