"""Bounded A/B planner-prompt trial with synthetic context and unchanged validation.

Maximum 72 requests, no retries, under $0.10 nominal token reservations using
Cloudflare's September 9 model-page prices. Does not select a runtime prompt.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import socket
import statistics
import subprocess
import sys
import threading
import time
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.conversation import Conversation
from local_app.core import messages_for
from local_app.engine import configure_runtime

BASELINE_REVISION='341aa93dde1fa6b82e00254186a5da6ceaf4319e'
_baseline_prefix=None


def baseline_instructions(snapshot,mode,scene,available):
    """Read the reviewed baseline's literal prompt; never execute historical code."""
    global _baseline_prefix
    if _baseline_prefix is None:
        source=subprocess.check_output(['git','show',BASELINE_REVISION+':local_app/conversation.py'],cwd=ROOT).decode('utf-8')
        tree=ast.parse(source)
        owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Conversation')
        method=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='plan')
        additions=[n for n in method.body if isinstance(n,ast.AugAssign)]
        if len(additions)!=1 or not isinstance(additions[0].value,ast.BinOp):raise ValueError('Unexpected baseline prompt structure.')
        _baseline_prefix=ast.literal_eval(additions[0].value.left)
        if not isinstance(_baseline_prefix,str):raise ValueError('Baseline prompt must be literal text.')
    pose=snapshot.get('visual_pose','unknown')
    return _baseline_prefix+json.dumps({'mode':mode,'scene':scene,'available_scenes':available,
        'visual_pose':pose if pose in {'base','near','portrait','unknown'} else 'unknown'})


def sparse_instructions(snapshot,mode,scene,available):
    text=baseline_instructions(snapshot,mode,scene,available)
    replacements={
        'Your reply should be natural, relevant and at most two short sentences (about 28 words). ':
            'Your reply should be natural, relevant and at most one short sentence (16 words). ',
        'Required output shape (replace these example values with your decision): ':
            'Available JSON fields (the following values are examples): ',
    }
    for old,new in replacements.items():
        if text.count(old)!=1:raise ValueError('Unexpected baseline wording.')
        text=text.replace(old,new)
    return text+(' Always include reply. Omit unchanged fields: presentation defaults to the selected mode, '
        'scene to keep, action to none, message to empty and facts to empty. '
        'Still include facts whenever the user shares or corrects a stable personal fact; do not omit such updates. '
        'Include message when explicitly requested during a call. A conversation without updates can be {"reply":"Hello."}.')

COMPACT = (
    '\nReturn a filled JSON object, never a schema. Always include reply. '
    'Optional fields default to: presentation=current mode, scene=keep, action=none, message="", facts=[]. '
    'Omit unchanged/default fields. Use only these keys. '
    'Reply to the latest user message naturally in one sentence, at most 16 words; for movement at most 10 words. '
    'Acknowledge a new personal detail directly instead of answering a different naming question. '
    'The user controls text/voice/video mode; never switch it. '
    'The app shows prepared pictures and voiced lip-sync video of Mira; do not deny these capabilities. '
    'Acknowledge displaying requested media, but never claim a body action succeeded before rendering. '
    'Only closer, farther and wave are supported movement actions. For anything else choose none '
    'and clearly say that movement is unavailable. Never promise an unsupported action. '
    'Use closer for approach/come here, farther for step back, wave for raising a hand. '
    'Only act on a current request; resolve references from history without repeating an old action. '
    'Honor the whole utterance, including negation and corrections: "Please do not. Wave" means stay still. '
    'Conflicting movement instructions mean stay still and clarify. In text/voice mode never perform, promise or claim movement; '
    'say "Switch to Video so I can try that movement." '
    'Scene choices: keep, mira (living room), garden, cafe, fullbody (full-body garden). '
    'Change scene only for an explicit visual request; describing places is conversation. '
    'Garden/fullbody are views of the same setting; garden conversation keeps current framing. '
    'Requested full-body view/stand up/movement selects fullbody. These are virtual settings, not physical travel. '
    'Pose near means close view, base means original full-body view, unknown means unmatched; do not invent another framing. '
    'During calls only, an explicit request to send/write/text a message puts its content in message (max 600 characters), '
    'with a short spoken acknowledgement in reply. Delivery is to the in-app Text tab, never SMS. '
    'Otherwise omit message. Example: "Send me a message saying hello" -> '
    '{"reply":"I sent it to your Text tab.","message":"Hello."}. '
    'When the latest user turn states or corrects a stable personal fact, include facts; do not omit the update. '
    'Use at most two {"key":"stable_lowercase_key","quote":"verbatim excerpt of the latest user turn"} objects. '
    'Keys include user_name, dog_name, piano_day and hobby; reuse a key for corrections. '
    'Example: user says "My dog is named Fern." -> {"reply":"Fern is a lovely name.",'
    '"facts":[{"key":"dog_name","quote":"My dog is named Fern."}]}. '
    'Otherwise omit facts. No inferred, medical/sexual, instruction or assistant facts. '
    'Never claim successful saving before the app records it. '
    'Naming direction: "What should you call me?" asks for the USER\'s name from saved notes; '
    '"What should I call you?" asks for your name, Mira. '
    'A normal response can be {"reply":"How did your recital go?"}. '
)


def compact_instructions(snapshot,mode,scene,available):
    pose=snapshot.get('visual_pose','unknown')
    return COMPACT+'\nCurrent app state (trusted capabilities): '+json.dumps({
        'mode':mode,'scene':scene,'available_scenes':available,
        'visual_pose':pose if pose in {'base','near','portrait','unknown'} else 'unknown'})


BASE={'memory':'My dog is named Maple. My name is Alex.','visual_pose':'near','turns':[
    {'user':'I have a piano recital on Friday.','assistant':'Which piece are you playing?'}]}
# Expected behavior is checked after the same validator used in the live app.
CASES=[
    dict(case='recall',user="What is my dog's name?",contains='Maple'),
    dict(case='context',user="I'm nervous about Friday. What was I preparing for?",contains='recital'),
    dict(case='negation',user='Please do not. Wave.'),
    dict(case='negated_approach',user="Don't come closer. Tell me something calming about this garden."),
    dict(case='unsupported',user='Please do a cartwheel.',unsupported=True),
    dict(case='message',user='Send me a message saying Good luck at your recital.',message='Good luck at your recital'),
    dict(case='naming_assistant',user='What should I call you?',contains='Mira'),
    dict(case='naming_user',user='What should you call me?',contains='Alex'),
    dict(case='unknown_fact',user='What is my favorite food?',unknown=True),
    dict(case='fact_correction',user="My dog is named Cedar now.",fact_quote='My dog is named Cedar now.'),
    dict(case='unseen_pet',user='Have you met my dog?',unseen=True),
    dict(case='scene_description',user='Describe this garden.'),
    dict(case='scene_change',user="Let's go to the coffee shop.",scene='cafe'),
    dict(case='movement_reference',user='Please do that again.',action='wave',snapshot={**BASE,'turns':[
        {'user':'Please wave hello.','assistant':'Let me try that.'}]}),
    dict(case='voice_movement',user='Could you come closer?',mode='voice',unsupported=True),
    dict(case='text_movement',user='Could you wave hello?',mode='text',unsupported=True),
    dict(case='conflicting_motion',user='Do not wave. Actually wave.'),
    dict(case='conversation',user='I had a busy day. Suggest one small way to relax.'),
]


def checks(plan,spec):
    reply=plan['reply'];result={
        'action':plan['action']==spec.get('action','none'),
        'scene':plan['scene']==spec.get('scene','fullbody'),
        'mode':plan['presentation']==spec.get('mode','video'),
        'nonempty_reply':bool(reply),'no_unrequested_message':bool(plan.get('message'))==bool(spec.get('message'))}
    if spec.get('contains'):result['recall']=spec['contains'].lower() in reply.lower()
    if spec.get('message'):result['message']=spec['message'].lower() in plan.get('message','').lower()
    if spec.get('unsupported'):result['unsupported_disclosed']=bool(re.search(r"cannot|can't|unavailable|not (?:able|supported)|need|video",reply,re.I))
    if spec.get('unknown'):result['unknown_disclosed']=bool(re.search(r"don't know|do not know|haven't (?:told|shared)|have not (?:told|shared)|not (?:sure|know)|what is",reply,re.I))
    if spec.get('unseen'):result['unseen_disclosed']=bool(re.search(r"haven't|have not|cannot|can't|never|no[, .]",reply,re.I))
    if spec.get('fact_quote'):result['verbatim_fact']=any(f['key']=='dog_name' and 'Cedar' in f['quote'] and f['quote'] in spec['user'] for f in plan['facts'])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--repeats',type=int,choices=[1,2],default=1)
    parser.add_argument('--case',choices=[x['case'] for x in CASES])
    parser.add_argument('--variant',choices=['compact','sparse'],default='compact')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a fresh lowercase label.')
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(('127.0.0.1',8766))==0:parser.error('Finish call timing first.')
    from scripts.review_lip_sync import preview_idle
    preview_idle();configure_runtime();auth=Conversation('unused')
    if auth.provider!='cloudflare' or auth.model!='@cf/qwen/qwen3-30b-a3b-fp8':parser.error('Use the selected Cloudflare Qwen configuration.')
    target=ROOT/'generated/local-app/audit'/('compact-planner-'+args.label+'.json')
    if target.exists():parser.error('Preserve previous evidence; choose another label.')
    candidate=compact_instructions if args.variant=='compact' else sparse_instructions
    sample_instructions=candidate(BASE,'video','fullbody',['mira','garden','cafe','fullbody'])
    result={'scope':__doc__,'baseline_revision':BASELINE_REVISION,'candidate_kind':args.variant,
        'candidate_sha256':hashlib.sha256(sample_instructions.encode()).hexdigest(),
        'candidate_instructions':sample_instructions,'runtime_changed':False,'rows':[],'complete':False,
        'pricing_source':'https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/',
        'pricing_checked':'2026-09-09','nominal_price_per_million':{'input':.051,'output':.34}}
    original=urllib.request.urlopen;reserved=0.;error_count=0
    try:
        for repeat in range(args.repeats):
            for spec in CASES:
                if args.case and spec['case']!=args.case:continue
                for kind in (['baseline',args.variant] if (repeat+CASES.index(spec))%2==0 else [args.variant,'baseline']):
                    snapshot=copy.deepcopy(spec.get('snapshot',BASE));mode=spec.get('mode','video');available=['mira','garden','cafe','fullbody']
                    row={'case':spec['case'],'repeat':repeat,'kind':kind,'prompt':spec['user']}
                    request_started=time.perf_counter()
                    def measured(request,**kwargs):
                        nonlocal reserved
                        expected=f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/v1/chat/completions'
                        if request.full_url!=expected or not request.data or len(request.data)>30000:raise ValueError('Unexpected request.')
                        body=json.loads(request.data)
                        if body['model']!=auth.model or body['max_tokens']>512:raise ValueError('Model/token bound exceeded.')
                        instructions=baseline_instructions if kind=='baseline' else candidate
                        body['messages'][0]['content']=messages_for(snapshot,spec['user'])[0]['content']+instructions(snapshot,mode,'fullbody',available)
                        payload=json.dumps(body).encode()
                        reservation=((len(payload)+1000)*.051+512*.34)/1e6
                        if reserved+reservation>.10:raise ValueError('Nominal token reservation exhausted.')
                        reserved+=reservation
                        sent=urllib.request.Request(request.full_url,data=payload,headers=dict(request.header_items()))
                        sent.add_header('cf-aig-skip-cache','true')
                        began=time.perf_counter()
                        with original(sent,timeout=30) as response:
                            if response.headers.get('cf-aig-cache-status','').upper()=='HIT':raise ValueError('Cached response is not a timing sample.')
                            data=response.read(1_000_001)
                        row['complete_s']=time.perf_counter()-began
                        if len(data)>1_000_000:raise ValueError('Oversized response.')
                        parsed=json.loads(data);usage=parsed.get('usage',{})
                        row['raw_plan_text']=str(parsed.get('choices',[{}])[0].get('message',{}).get('content',''))[:5000]
                        row['usage']={k:usage[k] for k in ['prompt_tokens','completion_tokens'] if type(usage.get(k)) is int and usage[k]>=0}
                        row['nominal_cost_usd']=(sum(row['usage'][k]*price for k,price in [('prompt_tokens',.051e-6),('completion_tokens',.34e-6)])
                            if len(row['usage'])==2 else None)
                        row['request_bytes']=len(payload)
                        return io.BytesIO(data)
                    try:
                        with patch('local_app.conversation.urllib.request.urlopen',side_effect=measured):
                            plan=auth.plan(snapshot,spec['user'],mode,'fullbody',available,threading.Event())
                        row['plan']=plan;row['checks']=checks(plan,spec)
                    except (OSError,ValueError,RuntimeError) as error:
                        row['error']=type(error).__name__
                        row['cause_type']=type(error.__cause__).__name__ if error.__cause__ else None
                        row['failed_elapsed_s']=time.perf_counter()-request_started
                        result['rows'].append(row)
                        target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
                        print(json.dumps({'case':spec['case'],'kind':kind,'error':row['error'],'cause_type':row['cause_type']}),flush=True)
                        error_count+=1
                        if error_count>=3:
                            raise RuntimeError('Three planner errors; comparison stopped with evidence retained.') from None
                        continue  # Next scheduled case, never retry this request.
                    result['rows'].append(row)
                    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
                    print(json.dumps({'case':spec['case'],'kind':kind,'seconds':round(row['complete_s'],3),
                        'failed_checks':[k for k,v in row['checks'].items() if not v]}),flush=True)
        result['complete']=True
    finally:
        result['reserved_nominal_usd']=reserved
        target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for kind in ['baseline',args.variant]:
        rows=[r for r in result['rows'] if r['kind']==kind]
        completed=[r for r in rows if 'checks' in r]
        print(json.dumps({'kind':kind,'samples':len(rows),'completed_samples':len(completed),
            'completed_median_s':statistics.median(r['complete_s'] for r in completed) if completed else None,
            'failed':sum('error' in r or not all(r.get('checks',{}).values()) for r in rows),
            'known_nominal_cost_usd':sum(r.get('nominal_cost_usd') or 0 for r in rows),
            'unknown_usage_requests':sum(r.get('nominal_cost_usd') is None for r in rows)}))


if __name__=='__main__':main()
