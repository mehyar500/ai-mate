"""Build an offline, synthetic-only call review page with exact frame stepping.

Run review_call_frames.py first. This report never marks media reviewed itself.
It embeds only synthetic prompts, timing diagnostics and relative media paths.
"""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def json_script(value):
    # Even synthetic dialogue is data, never markup or executable JavaScript.
    return json.dumps(value,ensure_ascii=True).replace('<','\\u003c').replace('&','\\u0026')


def reviewed_media(folder, item):
    name=f"{item['id']}-{item['chunk']}.mp4"
    if not re.fullmatch(r'[a-f0-9]{32}-\d+\.mp4',name):
        raise ValueError('Unexpected benchmark media name.')
    root=Path(folder).resolve()
    candidate=root/'retained-media'/name
    if not candidate.exists():candidate=root/name
    candidate=candidate.resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError('Reviewed media is missing or outside the benchmark.')
    if candidate.stat().st_size>64*1024*1024:
        raise ValueError('Review clips must be at most 64 MiB.')
    if hashlib.sha256(candidate.read_bytes()).hexdigest()!=item['video_sha256']:
        raise ValueError('Media changed after its frame audit.')
    return candidate.relative_to(root).as_posix()


CSS='''
:root{color-scheme:dark;font:16px system-ui;background:#101613;color:#f4f5f1}
*{box-sizing:border-box}body{margin:0}button,select,textarea,input{font:inherit}
button,select{min-height:44px;padding:.6rem;border:1px solid #526259;border-radius:10px;background:#26352d;color:inherit}
button:focus-visible,select:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #d7edb0;outline-offset:2px}
button:disabled{opacity:.4}h1{font-size:1.2rem;margin:0}header{padding:1rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
main{display:grid;grid-template-columns:minmax(280px,1fr) minmax(280px,420px);gap:1rem;padding:0 1rem 1rem;height:calc(100dvh - 85px)}
.stage{display:flex;flex-direction:column;min-height:0;background:#050705;border-radius:14px;overflow:hidden}
video{width:100%;height:100%;min-height:0;object-fit:contain}.transport{display:flex;flex-wrap:wrap;gap:.5rem;padding:.7rem;align-items:center}
.transport input{min-width:120px;flex:1}aside{overflow:auto;line-height:1.5}p{margin:.6rem 0}.muted{color:#b9c4bd;font-size:.9rem}
label{display:block;margin:.8rem 0 .25rem}textarea{width:100%;min-height:90px;background:#19251e;color:inherit;border:1px solid #637269;border-radius:8px;padding:.6rem}
.checks label{display:flex;align-items:center;gap:.6rem;min-height:44px;margin:.15rem 0}.checks input{width:20px;height:20px}
#clips{max-width:100%;flex:1}#frame-info{font-variant-numeric:tabular-nums}#status{min-height:24px;color:#d7edb0}
@media(max-width:720px){main{height:auto;display:block}.stage{height:70dvh}aside{padding-top:1rem}header{padding:.7rem}h1{width:100%}}
'''

JS='''
const report=JSON.parse(document.getElementById('report').textContent);
const $=id=>document.getElementById(id),video=$('video'),clips=$('clips');
let selected=0,frame=0,notes={},mediaURL=null,mediaRequest=null;
const storageKey='ai-mate-synthetic-review:'+report.run;
try{notes=JSON.parse(localStorage.getItem(storageKey)||'{}');if(!notes||typeof notes!=='object'||Array.isArray(notes))notes={};}catch{}
for(const [index,item] of report.items.entries()){
  const option=document.createElement('option');option.value=index;
  option.textContent=`${index+1}. Cycle ${item.cycle} · ${item.case}`;clips.append(option);
}
const current=()=>report.items[selected];
const mark=()=>notes[current().key]||{};
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(notes));$('status').textContent='Review notes saved in this browser.';}catch{$('status').textContent='Browser storage is unavailable. Export notes before closing.';}}
function save(){
  notes[current().key]={reviewed:$('reviewed').checked,normalSpeed:$('normal').checked,audioHeard:$('heard').checked,
    note:$('note').value.slice(0,4000),flags:mark().flags||[],updated:new Date().toISOString()};persist();
}
function showFrame(time){
  const times=current().times;let index=0;
  for(let i=1;i<times.length&&times[i]<=time+.001;i++)index=i;
  frame=index;$('scrub').value=index;$('frame-info').textContent=`Frame ${index+1}/${times.length} · ${time.toFixed(3)}s`;
  $('back-frame').disabled=index===0;$('next-frame').disabled=index===times.length-1;
}
function seek(index){
  video.pause();const times=current().times;index=Math.max(0,Math.min(times.length-1,index));
  const step=index+1<times.length?times[index+1]-times[index]:1/current().fps;
  video.currentTime=times[index]+step*.45;
}
async function choose(index){
  selected=index;clips.value=index;const item=current(),record=mark();
  mediaRequest?.abort();const request=new AbortController();mediaRequest=request;
  video.pause();video.removeAttribute('src');video.load();
  if(mediaURL){URL.revokeObjectURL(mediaURL);mediaURL=null;}
  video.playbackRate=1;frame=0;
  $('scrub').max=item.times.length-1;$('scrub').value=0;
  $('prompt').textContent=item.prompt;$('reply').textContent=item.reply;
  $('timing').textContent=item.metrics;
  $('audit').textContent=`${item.times.length} decoded frames · ${item.flags.length} heuristic flags. ${item.flags.length?'Flagged indices: '+item.flags.join(', '):'No automated flag is a visual-quality guarantee.'}`;
  $('note').value=record.note||'';$('reviewed').checked=record.reviewed===true;$('normal').checked=record.normalSpeed===true;$('heard').checked=record.audioHeard===true;
  $('previous').disabled=index===0;$('next').disabled=index===report.items.length-1;
  $('status').textContent='Loading recorded clip…';showFrame(0);
  $('back-frame').disabled=true;$('next-frame').disabled=true;$('scrub').disabled=true;
  try{
    // A complete Blob supports frame seeking even on a simple localhost server
    // without HTTP Range support. Only one short audited clip is held at a time.
    const response=await fetch(item.media,{signal:request.signal});
    if(!response.ok)throw Error('Media request failed');
    const blob=await response.blob();
    if(request.signal.aborted)return;
    if(blob.size>64*1024*1024)throw Error('Review clip exceeds 64 MiB');
    mediaURL=URL.createObjectURL(blob);video.src=mediaURL;
    $('status').textContent='';
  }catch(error){if(!request.signal.aborted)$('status').textContent='Media could not load. Serve this synthetic audit folder on localhost and retry.';}
}
clips.addEventListener('change',()=>choose(Number(clips.value)));
$('previous').onclick=()=>choose(selected-1);$('next').onclick=()=>choose(selected+1);
$('back-frame').onclick=()=>seek(frame-1);$('next-frame').onclick=()=>seek(frame+1);
$('scrub').addEventListener('input',()=>seek(Number($('scrub').value)));
$('flag').onclick=()=>{save();notes[current().key].flags.push({frame,time_s:current().times[frame],note:$('note').value.slice(0,4000)});persist();};
for(const id of ['reviewed','normal','heard','note'])$(id).addEventListener('change',save);
video.addEventListener('seeked',()=>showFrame(video.currentTime));
video.addEventListener('loadeddata',()=>{$('scrub').disabled=false;showFrame(video.currentTime);});
video.addEventListener('error',()=>{$('status').textContent='Media could not load. Serve this synthetic audit folder on localhost and retry.';});
if(video.requestVideoFrameCallback){const callback=(_,meta)=>{showFrame(meta.mediaTime);video.requestVideoFrameCallback(callback);};video.requestVideoFrameCallback(callback);}
else video.addEventListener('timeupdate',()=>showFrame(video.currentTime));
$('export').onclick=()=>{
  save();const result={run:report.run,scope:'User-entered review notes; self-reported playback and audible output, not automated certification.',notes};
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
  const anchor=document.createElement('a');anchor.href=url;anchor.download=report.run+'-review-notes.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
choose(0);
'''


def build(folder):
    folder=Path(folder)
    qualification=json.loads((folder/'qualification.json').read_text(encoding='utf-8'))
    call_summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if call_summary['turns']!=len(qualification['results']):
        raise ValueError('The call suite is incomplete or changed after its summary.')
    audit=json.loads((folder/'frame-review.json').read_text(encoding='utf-8'))
    jobs={r['id']:r for r in qualification['results'] if 'id' in r}
    expected={(row['id'],chunk['index']) for row in jobs.values() for chunk in row.get('job',{}).get('chunks',[])}
    observed=[(item['id'],item['chunk']) for item in audit['reviews']]
    if len(observed)!=len(set(observed)) or set(observed)!=expected:
        raise ValueError('The frame audit does not cover every retained reply chunk.')
    items=[]
    for item in audit['reviews']:
        if item.get('media_missing'):raise ValueError('The audit has missing media; cannot produce a complete review.')
        row=jobs[item['id']];summary=item['summary'];frames=item['frames']
        if not frames or len(frames)>1800 or len(frames)!=summary['decoded_frames']:
            raise ValueError('Invalid audited frame count.')
        items.append({'key':f"{item['id']}-{item['chunk']}",'case':row['case'],'cycle':row.get('cycle',1),
                      'media':reviewed_media(folder,item),'prompt':row['expected']['prompt'],'reply':row['job']['text'],
                      'times':[f['time_s'] for f in frames],'fps':summary['fps'],'flags':summary['flagged_frames'],
                      'metrics':row.get('metrics','No playback timing retained.')})
    if not 1<=len(items)<=240:raise ValueError('Unexpected number of review clips.')
    failed=sum(bool(row.get('failures')) for row in qualification['results'])
    unrendered=sum(not row.get('job',{}).get('chunks') for row in qualification['results'])
    data={'run':folder.name,'items':items,'turns':call_summary['turns'],'failed_turns':failed,'turns_without_media':unrendered}
    digest=base64.b64encode(hashlib.sha256(JS.encode()).digest()).decode()
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'self'; media-src 'self' blob:; style-src 'unsafe-inline'; script-src 'sha256-{digest}'; base-uri 'none'; form-action 'none'">
<title>AI Mate · synthetic call review</title><style>{CSS}</style>
<header><h1>Synthetic call review</h1><select id="clips" aria-label="Select clip"></select><button id="export">Export notes</button></header>
<main><section class="stage" aria-label="Recorded call"><video id="video" controls playsinline preload="metadata"></video>
<div class="transport"><button id="back-frame" aria-label="Previous frame">−1 frame</button><input id="scrub" aria-label="Frame position" type="range" min="0" step="1" value="0"><button id="next-frame" aria-label="Next frame">+1 frame</button></div></section>
<aside><div class="transport"><button id="previous">Previous clip</button><button id="next">Next clip</button></div><p id="frame-info"></p>
<p class="muted">{html.escape(folder.name)} · {len(items)} retained clips from {call_summary['turns']} commands · {failed} failed commands · {unrendered} commands without media. Playback uses the recorded MP4 audio. This is an offline review tool, not a live call or a physical speaker test.</p>
<label for="prompt">Synthetic command</label><p id="prompt"></p><label for="reply">Reply</label><p id="reply"></p><p id="timing" class="muted"></p><p id="audit" class="muted"></p>
<div class="checks"><label><input id="normal" type="checkbox">I watched at normal speed</label><label><input id="heard" type="checkbox">I heard the speech</label><label><input id="reviewed" type="checkbox">I reviewed this clip</label></div>
<label for="note">Defects and observations</label><textarea id="note" maxlength="4000" placeholder="Identity, hands, mouth, framing, flicker, seams or speech alignment"></textarea>
<button id="flag">Flag current frame</button><p id="status" role="status"></p></aside></main>
<script id="report" type="application/json">{json_script(data)}</script><script>{JS}</script></html>'''
    target=folder/'review.html';target.write_text(page,encoding='utf-8')
    return {'clips':len(items),'frames':sum(len(i['times']) for i in items),'output':str(target)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',choices=['qualification','soak'],required=True)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    folder=ROOT/'generated/local-app/audit'/f'voice-video-{args.trial}-{args.label}'
    print(json.dumps(build(folder)))


if __name__=='__main__':main()
