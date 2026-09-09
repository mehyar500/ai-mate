"""Bounded neutral CPU TTS comparison; no hosted request or active voice change."""
import argparse
import hashlib
import importlib.util
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
from scripts.download_supertonic_benchmark import FOLDER,verified_files
from experiments.benchmark_call_asr import words,word_errors

CASES={
    'short':'Let me try that.',
    'greeting':"I'm doing well, thanks for asking! How about you?",
    'normal':'The garden is quiet with birdsong. Flowers sway in the breeze.',
    'memory':'Your dog is named Maple. You told me that your interview is next Tuesday, and you want to practice before you go.',
    'long':'One, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, twenty, twenty-one, twenty-two, twenty-three, twenty-four, twenty-five.',
}


class SupertonicSpeech:
    """An isolated benchmark adapter for the experimental preset voice."""
    def __init__(self,threads=4,steps=8):
        self.spec=verified_files()
        import onnxruntime as ort
        spec=importlib.util.spec_from_file_location('verified_supertonic_helper',FOLDER/'helper.py')
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        options=ort.SessionOptions();options.intra_op_num_threads=threads;options.inter_op_num_threads=1
        options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        cfg=helper.load_cfgs(str(FOLDER/'onnx'))
        sessions=helper.load_onnx_all(str(FOLDER/'onnx'),options,['CPUExecutionProvider'])
        self.tts=helper.TextToSpeech(cfg,helper.load_text_processor(str(FOLDER/'onnx')),*sessions)
        self.style=helper.load_voice_style([str(FOLDER/'voice_styles/F1.json')])
        self.steps=steps

    def create(self,text):
        import numpy as np
        if not isinstance(text,str) or not 1<=len(text)<=300:raise ValueError('Use a bounded benchmark phrase.')
        wav,duration=self.tts(text,'en',self.style,self.steps,speed=1.0)
        rate=self.tts.sample_rate
        audio=wav[0,:int(rate*float(duration[0]))]
        if not .15<=len(audio)/rate<=30 or not np.isfinite(audio).all():raise ValueError('Invalid generated speech.')
        return audio,rate

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    parser.add_argument('--threads',type=int,choices=[2,4,8],default=4)
    parser.add_argument('--repeats',type=int,choices=[1,2,3],default=3)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.25)
    except OSError:pass
    else:connection.close();raise RuntimeError('Finish call timing before benchmarking CPU speech.')
    folder=ROOT/'generated/local-app/audit'/('speech-supertonic-'+args.label);folder.mkdir(exist_ok=False)
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
    from local_app.models import Models
    started=time.perf_counter();supertonic=SupertonicSpeech(args.threads);load_s=time.perf_counter()-started
    options=ort.SessionOptions();options.intra_op_num_threads=args.threads;options.inter_op_num_threads=1
    cache=ROOT/'.cache/local-poc'
    session=ort.InferenceSession(str(cache/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    kokoro=Kokoro.from_session(session,str(cache/'voices-v1.0.bin'))
    def synth(model,text):
        if model=='kokoro':return kokoro.create(text,voice='af_sarah',speed=1,lang='en-us')
        supertonic.steps=int(model.rsplit('-',1)[1]);return supertonic.create(text)
    settings=['kokoro','supertonic-5','supertonic-8'];rows=[]
    for model in settings:synth(model,'Hello there.')
    for repeat in range(args.repeats):
        for case,text in CASES.items():
            for model in (settings if repeat%2==0 else list(reversed(settings))):
                np.random.seed(90300+repeat)
                started=time.perf_counter();audio,rate=synth(model,text);seconds=time.perf_counter()-started
                target=folder/f'{model}-{case}-{repeat}.wav';sf.write(target,audio,rate,subtype='PCM_16')
                row={'model':model,'case':case,'repeat':repeat,'expected':text,'seconds':seconds,'duration_s':len(audio)/rate,
                     'rate':rate,'rms':float(np.sqrt(np.mean(audio**2))),'peak':float(np.max(np.abs(audio))),
                     'clipped_fraction':float(np.mean(np.abs(audio)>=.999)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
                rows.append(row)
            print(json.dumps({'repeat':repeat,'case':case,'samples':len(rows)}),flush=True)
    # Readback runs only after timing; it is an intelligibility proxy, not listening.
    adapter=Models.__new__(Models);adapter.asr=WhisperModel(str(cache/'asr-base-en'),device='cpu',compute_type='int8',cpu_threads=8,num_workers=1,local_files_only=True)
    for row in rows:
        target=folder/f"{row['model']}-{row['case']}-{row['repeat']}.wav"
        row['transcript']=adapter.transcribe(target.read_bytes())
        row['word_errors']=word_errors(row['expected'],row['transcript']);row['expected_words']=len(words(row['expected']))
        if row['case']=='long':
            row['readback_numbers']=[int(n) for n in re.findall(r'\b\d+\b',row['transcript'])]
            row['readback_count_complete']=row['readback_numbers']==list(range(1,26))
    summaries=[]
    for model in settings:
        selected=[r for r in rows if r['model']==model];times=sorted(r['seconds'] for r in selected)
        summaries.append({'model':model,'samples':len(selected),'median_s':statistics.median(times),'p95_s':times[math.ceil(len(times)*.95)-1],
                          'by_case_median_s':{case:statistics.median(r['seconds'] for r in selected if r['case']==case) for case in CASES},
                          'readback_word_error_rate':sum(r['word_errors'] for r in selected)/sum(r['expected_words'] for r in selected),
                          'non_count_readback_word_error_rate':sum(r['word_errors'] for r in selected if r['case']!='long')/sum(r['expected_words'] for r in selected if r['case']!='long'),
                          'complete_count_repeats':sum(r.get('readback_count_complete',False) for r in selected)})
    result={'threads':args.threads,'onnxruntime':ort.__version__,'supertonic_load_s':load_s,'supertonic':supertonic.spec,'summaries':summaries,'rows':rows,
            'scope':'Neutral generated preset voices; warm complete-wave synthesis only. Same texts, different voice/timing. Seeded Supertonic at speed1, 5/8 steps. Readback word errors can include ASR errors and numeric formatting; no physical listening, visual lip-sync, public-content permission or live selection.'}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(summaries),flush=True)


if __name__=='__main__':main()
