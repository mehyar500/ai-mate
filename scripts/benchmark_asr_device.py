"""Compare CPU/GPU Whisper on existing fixed synthetic corpora; no API calls."""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.models import Models,CACHE
from scripts.benchmark_call_asr import word_errors,words
from scripts.benchmark_asr_window import artifact_flags


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--compare-with',help='Existing asr-device label, using identical fixture hashes.')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    baseline={}
    if args.compare_with:
        if not re.fullmatch(r'[a-z0-9-]{1,32}',args.compare_with):parser.error('Use a short comparison label.')
        previous=json.loads((ROOT/'generated/local-app/audit'/('asr-device-'+args.compare_with)/'results.json').read_text())
        for item in previous['results']:
            for row in item['rows']:
                baseline[(item['device'],item['compute_type'],row['corpus'],row['name'])]=row
    folder=ROOT/'generated/local-app/audit'/('asr-device-'+args.label)
    folder.mkdir(exist_ok=False)
    import torch
    # Use the already installed, pinned CUDA/cuDNN libraries on Windows.
    dll=os.add_dll_directory(str(Path(torch.__file__).parent/'lib')) if os.name=='nt' else None
    import ctranslate2
    from faster_whisper import WhisperModel
    fixtures=[]
    for corpus in ['cpu-comparison','challenge']:
        source=ROOT/'generated/local-app/audit'/('asr-calls-'+corpus)
        for item in json.loads((source/'fixtures.json').read_text()):
            if not re.fullmatch(r'[a-z0-9_-]+',item['name']):raise ValueError('Unexpected fixture name.')
            raw=(source/(item['name']+'.wav')).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Changed fixture.')
            fixtures.append({**item,'corpus':corpus,'raw':raw})
    assert len(fixtures)==119
    def memory():
        try:
            value=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True,timeout=5)
            return int(value.strip().splitlines()[0])
        except (ValueError,OSError,subprocess.SubprocessError):return None
    baseline_memory=memory();results=[]
    for device,precision in [('cpu','int8'),('cuda','int8_float16'),('cuda','float16')]:
        began=time.perf_counter();adapter=Models.__new__(Models)
        adapter.asr=WhisperModel(str(CACHE/'asr-base-en'),device=device,compute_type=precision,cpu_threads=8,num_workers=1,local_files_only=True)
        load_s=time.perf_counter()-began
        began=time.perf_counter();adapter.transcribe(fixtures[0]['raw']);cold_s=time.perf_counter()-began
        rows=[]
        for item in fixtures:
            began=time.perf_counter();text=adapter.transcribe(item['raw']);elapsed=time.perf_counter()-began
            row={k:v for k,v in item.items() if k!='raw'}
            row.update(text=text,seconds=elapsed,word_errors=word_errors(item['expected'],text),words=len(words(item['expected'])),artifact_flags=artifact_flags(text))
            if baseline:
                prior=baseline[(device,precision,item['corpus'],item['name'])]
                if prior['sha256']!=item['sha256']:raise ValueError('Comparison fixture changed.')
                row.update(previous_text=prior['text'],same_words=words(prior['text'])==words(text))
            if item.get('check_negation') or item['case'] in {'negated_return','negated_wave'}:
                row['negation_kept']=bool(set(words(text))&{'dont','not','never','no'})
            rows.append(row)
        summaries={}
        for corpus in ['cpu-comparison','challenge']:
            subset=[r for r in rows if r['corpus']==corpus];latencies=sorted(r['seconds'] for r in subset if r['expected'])
            summaries[corpus]={'samples':len(subset),'median_s':statistics.median(latencies),'p95_s':latencies[math.ceil(len(latencies)*.95)-1],
                'word_errors':sum(r['word_errors'] for r in subset),'reference_words':sum(r['words'] for r in subset),
                'negation_failures':sum(r.get('negation_kept') is False for r in subset),'artifact_outputs':sum(bool(r['artifact_flags']) for r in subset),
                'non_speech_hallucinations':sum(bool(r['text']) for r in subset if not r['expected'])}
            if baseline:summaries[corpus]['changed_word_outputs']=sum(not r['same_words'] for r in subset)
        item={'device':device,'compute_type':precision,'load_s':load_s,'cold_transcribe_s':cold_s,'device_memory_after_mib':memory(),'summary':summaries,'rows':rows}
        results.append(item)
        record={'scope':'119 fixed synthetic fixtures, real WAV validation and Whisper recognition, no private inputs/API calls/live selection. Device-wide memory includes idle preview and CUDA context, not exclusive model usage.',
            'adapter_sha256':hashlib.sha256((ROOT/'local_app/models.py').read_bytes()).hexdigest(),
            'audio_input':'validated mono PCM, scipy polyphase resampling, float32 16 kHz ndarray',
            'compare_with':args.compare_with,
            'torch':torch.__version__,'ctranslate2':ctranslate2.__version__,'device_memory_before_mib':baseline_memory,'results':results}
        (folder/'results.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({k:v for k,v in item.items() if k!='rows'}),flush=True)
        del adapter;gc.collect()
    if dll:dll.close()


if __name__=='__main__':main()
