"""Bounded synthetic early-planning experiment; never changes the live app.

At 200ms after synthetic speech ends, prepare ASR/plan/speech. At the existing
650ms boundary, independently recognize the complete audio. Reuse only an exact
transcript match. Changed prefixes discard the draft before normal preparation.
This measures speech-file readiness, not browser playback or physical speech.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import math
from pathlib import Path
import re
import socket
import statistics
import sys
import threading
import time
from unittest.mock import patch
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.engine import configure_runtime
from local_app.models import Cancelled, Models, check_cancel
from scripts.benchmark_call_asr import word_errors


def run_pair(models, item, folder, kind):
    """No engine, memory write, renderer or playback exists in this experiment."""
    early_at=item.get('draft_at_s',.2)
    lead=max(0,-early_at) if kind=='early' and early_at is not None else 0
    started=time.perf_counter()+lead
    row={'case':item['case'],'kind':kind,'challenge':item['challenge'],
         'draft_at_s':early_at,'cancel_at_s':item.get('cancel_at_s')}
    cancel=threading.Event(); draft={}
    snapshot={'memory':'My dog is named Maple. My favorite tea is jasmine.',
              'turns':[], 'visual_pose':item['pose']}

    def at(seconds):
        remaining=started+seconds-time.perf_counter()
        if remaining>0:time.sleep(remaining)

    def transcribe(raw, target, prefix):
        began=time.perf_counter(); text=models.transcribe(raw)
        target[prefix+'_asr_s']=time.perf_counter()-began
        return text

    def prepare(text, destination, target, event):
        check_cancel(event); began=time.perf_counter()
        plan=models.plan(snapshot,text,'video','fullbody',['fullbody','garden','mira','cafe'],event)
        target['planner_s']=time.perf_counter()-began; target['plan']=plan
        check_cancel(event); began=time.perf_counter()
        target['speech_duration_s']=models.speech(plan['reply'],destination)
        target['tts_s']=time.perf_counter()-began
        check_cancel(event)
        target['ready_s']=time.perf_counter()-started
        return plan

    if kind=='serial' or early_at is None:
        at(item.get('submit_at_s',.65)); text=transcribe(item['full'],row,'final')
        row['transcript']=text
        prepare(text,folder/(item['case']+'-'+kind+'.wav'),row,cancel)
        row['reused']=False
    else:
        def early():
            at(early_at)
            draft['transcript']=transcribe(item['early'],draft,'early')
            check_cancel(cancel)
            prepare(draft['transcript'],folder/(item['case']+'-draft.wav'),draft,cancel)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(early)
            timer=None
            if item.get('cancel_at_s') is not None:
                timer=threading.Timer(max(0,started+item['cancel_at_s']-time.perf_counter()),cancel.set)
                timer.start()
            at(item.get('submit_at_s',.65)); text=transcribe(item['full'],row,'final'); row['transcript']=text
            row['final_verified_s']=time.perf_counter()-started
            # Exact text only: no punctuation normalization or fuzzy acceptance.
            same=draft.get('transcript')==text and bool(text) and not cancel.is_set()
            if not same:cancel.set()
            discarded_wait=time.perf_counter()
            try:future.result(timeout=45)
            except Cancelled:pass
            row['draft_join_s']=time.perf_counter()-discarded_wait
            row['reused']=same and not cancel.is_set() and 'ready_s' in draft
            if row['reused']:
                row['plan']=draft['plan'];row['speech_duration_s']=draft['speech_duration_s']
                row['ready_s']=time.perf_counter()-started
            else:
                prepare(text,folder/(item['case']+'-fallback.wav'),row,threading.Event())
            row['draft']=draft
            # Drafts remain isolated recordings; there is no route to send them.
            if not same and row['reused']:raise AssertionError('Changed transcript reused.')
            if timer:timer.cancel()
    row['final_word_errors']=word_errors(item['expected'],row['transcript']) if item['expected'] is not None else None
    row['expected']=item['expected']
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--replay-label',help='Prepared actual-detector timeline; preferred comparison.')
    mode.add_argument('--ideal-ending',action='store_true',help='Optimistic final-pause experiment, not detector replay.')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.25)
    except OSError:pass
    else:connection.close();raise SystemExit('Finish the active call benchmark first.')
    with urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap',timeout=5) as response:
        state=json.load(response)
    if state['busy']:raise SystemExit('Run this CPU experiment between calls.')
    del state  # Never retain or benchmark the private snapshot.
    folder=ROOT/'generated/local-app/audit'/('preemptive-'+args.label)
    folder.mkdir(exist_ok=False)
    import numpy as np
    import soundfile as sf

    def wav(audio,rate):
        stream=io.BytesIO();sf.write(stream,audio,rate,format='WAV',subtype='PCM_16');return stream.getvalue()

    def early_audio(raw, first_pause=False):
        audio,rate=sf.read(io.BytesIO(raw),dtype='float32')
        block=max(1,round(rate*128/48000));last=0;quiet=0;seen=False;cut=None
        for start in range(0,len(audio),block):
            end=min(len(audio),start+block)
            loud=float(np.sqrt(np.mean(audio[start:end]**2)))>.009
            if loud:last=end;seen=True;quiet=0
            elif seen:
                quiet+=end-start
                if first_pause and cut is None and quiet>=rate*.2:
                    cut=end
        if not last:raise ValueError('Synthetic fixture has no speech energy.')
        if first_pause:
            if cut is None or cut>=last:raise ValueError('Challenge needs a prefix followed by more speech.')
        else:cut=last+round(rate*.2)
        full_length=max(len(audio),last+round(rate*.65))
        padded=np.pad(audio,(0,max(0,full_length-len(audio))))
        return wav(padded[:cut],rate),wav(padded,rate)

    fixtures=[];source=ROOT/'generated/local-app/audit/voice-video-qualification-headroom'
    pose='base'
    for spec in json.loads((ROOT/'config/video-call-qualification.json').read_text()):
        raw=(source/(spec['case']+'.wav')).read_bytes();early,full=early_audio(raw)
        fixtures.append({'case':spec['case'],'expected':spec['prompt'],'early':early,'full':full,'pose':pose,'challenge':False})
        pose=spec.get('pose') or 'unknown'
    challenge=ROOT/'generated/local-app/audit/asr-calls-challenge'
    for spec in json.loads((challenge/'fixtures.json').read_text()):
        if spec['case'] not in {'paused_negation','paused_correction'}:continue
        raw=(challenge/(spec['name']+'.wav')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=spec['sha256']:raise ValueError('Changed challenge fixture.')
        early,full=early_audio(raw,True)
        fixtures.append({'case':spec['name'],'expected':spec['expected'],'early':early,'full':full,'pose':'base','challenge':True})
    assert len(fixtures)==26
    if args.replay_label:
        if not re.fullmatch(r'[a-z0-9-]{1,32}',args.replay_label):parser.error('Use a short lowercase replay label.')
        replay=ROOT/'generated/local-app/audit'/('preemptive-replay-'+args.replay_label)
        timeline=json.loads((replay/'fixtures.json').read_text())
        if hashlib.sha256((ROOT/'local_app/web/microphone.mjs').read_bytes()).hexdigest()!=timeline['detector_sha256']:
            raise ValueError('Detector changed after fixture preparation.')
        fixtures=[]
        for spec in timeline['turns']:
            item=dict(spec)
            for key in ['full','draft']:
                name=spec.get(key+'_file')
                if name is None:continue
                if not re.fullmatch(r'[a-z0-9_-]{1,100}\.wav',name):raise ValueError('Unexpected replay filename.')
                raw=(replay/name).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=spec[key+'_sha256']:raise ValueError('Changed replay audio.')
                item['early' if key=='draft' else 'full']=raw
            fixtures.append(item)
        assert 1<=len(fixtures)<=40
    configure_runtime();models=Models();auth=models.conversation
    if auth.provider!='cloudflare' or auth.model!='@cf/qwen/qwen3-30b-a3b-fp8':
        raise SystemExit('Use the configured Qwen/Cloudflare baseline.')
    models.transcribe(fixtures[0]['full'])
    original=urllib.request.urlopen;network=[];net_lock=threading.Lock();rows=[]
    def measured(request,**kwargs):
        expected=f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/v1/chat/completions'
        if request.full_url!=expected or not request.data or len(request.data)>30000:
            raise ValueError('Unexpected benchmark request.')
        body=json.loads(request.data)
        if body['model']!=auth.model or body['max_tokens']>512:raise ValueError('Request exceeds model/token bounds.')
        with net_lock:
            if len(network)>=80:raise ValueError('Request cap reached.')
            item={'reserved_completion_tokens':512};network.append(item)
        began=time.perf_counter()
        with original(request,timeout=30) as response:data=response.read(1_000_001)
        if len(data)>1_000_000:raise ValueError('Oversized provider response.')
        result=json.loads(data);item['seconds']=time.perf_counter()-began
        item['usage']={k:v for k,v in result.get('usage',{}).items() if k in {'prompt_tokens','completion_tokens','total_tokens'} and isinstance(v,int)}
        return io.BytesIO(data)
    def save():
        record={'scope':'Synthetic ASR/planner/TTS overlap only. 200ms draft, unchanged 650ms boundary and independent full ASR validation. No engine/memory mutation, renderer, microphone, browser timing or live selection. Ideal-ending mode assumes the final pause is known; its changed-prefix timing is a rejection stress test, not realistic turn replay.',
                'replay_label':args.replay_label,'ideal_ending':args.ideal_ending,
                'model':auth.model,'asr':'Whisper Base EN int8 CPU8, original padding','tts':'Kokoro-82M af_sarah CPU8',
                'rows':rows,'network':network}
        (folder/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    try:
        with patch('local_app.conversation.urllib.request.urlopen',side_effect=measured):
            for index,item in enumerate(fixtures):
                for kind in (['serial','early'] if index%2==0 else ['early','serial']):
                    row=run_pair(models,item,folder,kind);rows.append(row);save()
                pair=rows[-2:]
                print(json.dumps({'case':item['case'],'challenge':item['challenge'],'runs':[{k:r[k] for k in ['kind','ready_s','reused','final_word_errors']} for r in pair]}),flush=True)
    except Exception as error:
        save();print(json.dumps({'error_type':type(error).__name__,'completed_runs':len(rows),'active_app_unchanged':True}),flush=True)
        raise SystemExit('Early-planning experiment stopped; sanitized evidence retained.') from None
    summary={'cases':len(fixtures),'requests':len(network),'active_app_unchanged':True}
    for kind in ['serial','early']:
        chosen=[r for r in rows if r['kind']==kind and not r['challenge']];timings=sorted(r['ready_s'] for r in chosen)
        summary[kind]={'samples':len(chosen),'speech_file_ready_median_s':statistics.median(timings),'speech_file_ready_p95_s':timings[math.ceil(len(timings)*.95)-1],
                       'reused':sum(r['reused'] for r in chosen),'word_errors':sum(r['final_word_errors'] or 0 for r in chosen),
                       'unscored_split_turns':sum(r['final_word_errors'] is None for r in chosen)}
    mismatches=[r for r in rows if r['challenge'] and r['kind']=='early']
    summary['challenge']={'samples':len(mismatches),'reused':sum(r['reused'] for r in mismatches),'discarded':sum(not r['reused'] for r in mismatches)}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
