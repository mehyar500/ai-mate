// Replay the actual SpeechTurns detector on fixed synthetic WAVs. No devices,
// server requests, inference, private memory or active UI changes.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {SpeechTurns,encodeWav} from '../local_app/web/microphone.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const label=process.argv[2];assert.match(label||'',/^[a-z0-9-]{1,32}$/);
const audit=path.join(root,'generated/local-app/audit');
const folder=path.join(audit,'preemptive-replay-'+label);fs.mkdirSync(folder);
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function decode(bytes){
  assert.equal(bytes.toString('ascii',0,4),'RIFF');assert.equal(bytes.toString('ascii',8,12),'WAVE');
  let format,data;
  for(let at=12;at+8<=bytes.length;){
    const name=bytes.toString('ascii',at,at+4),size=bytes.readUInt32LE(at+4),begin=at+8;
    assert.ok(begin+size<=bytes.length);
    if(name==='fmt ')format=bytes.subarray(begin,begin+size);
    if(name==='data')data=bytes.subarray(begin,begin+size);
    at=begin+size+(size%2);
  }
  assert.ok(format?.length>=16&&data?.length);
  assert.equal(format.readUInt16LE(0),1);assert.equal(format.readUInt16LE(2),1);
  assert.equal(format.readUInt16LE(14),16);
  const rate=format.readUInt32LE(4);assert.ok(rate>=8000&&rate<=96000);
  assert.ok(data.length/(2*rate)<=30);
  const samples=new Float32Array(data.length/2+Math.ceil(rate*.8));
  for(let i=0;i<data.length/2;i++)samples[i]=data.readInt16LE(i*2)/32768;
  return {samples,rate};
}
const sources=JSON.parse(fs.readFileSync(path.join(root,'config/video-call-qualification.json')))
  .map(s=>({...s,expected:s.prompt,challenge:false,file:path.join(audit,'voice-video-qualification-headroom',s.case+'.wav')}));
const challengeRoot=path.join(audit,'asr-calls-challenge');
for(const spec of JSON.parse(fs.readFileSync(path.join(challengeRoot,'fixtures.json')))){
  if(!['paused_negation','paused_correction'].includes(spec.case))continue;
  assert.match(spec.name,/^[a-z_]+-paused_(negation|correction)$/);
  sources.push({...spec,case:spec.name,challenge:true,file:path.join(challengeRoot,spec.name+'.wav')});
}
assert.equal(sources.length,26);
const turns=[],sourceResults=[];let pose='base';
for(const spec of sources){
  const bytes=fs.readFileSync(spec.file);if(spec.sha256)assert.equal(hash(bytes),spec.sha256);
  const {samples,rate}=decode(bytes),block=Math.max(1,Math.round(rate*128/48000));
  let clock=0,lastVoice=0,draft=null;const sourceTurns=[];
  const detector=new SpeechTurns(rate,raw=>{
    const key=spec.case+'-turn-'+sourceTurns.length;
    const fullName=key+'-full.wav';fs.writeFileSync(path.join(folder,fullName),Buffer.from(raw));
    const row={case:key,source_case:spec.case,challenge:spec.challenge,pose,source_expected:spec.expected,
      full_file:fullName,full_sha256:hash(Buffer.from(raw)),submit_at_s:clock-lastVoice,
      draft_at_s:null,cancel_at_s:null,draft_file:null};
    if(draft){
      row.draft_at_s=draft.at-lastVoice;row.cancel_at_s=draft.resumed===null?null:draft.resumed-lastVoice;
      row.draft_file=key+'-draft.wav';row.draft_sha256=hash(Buffer.from(draft.raw));
      fs.writeFileSync(path.join(folder,row.draft_file),Buffer.from(draft.raw));
    }
    sourceTurns.push(row);draft=null;
  });
  for(let start=0;start<samples.length;start+=block){
    const end=Math.min(samples.length,start+block),chunk=samples.slice(start,end);clock=end/rate;
    let power=0;for(const value of chunk)power+=value*value;
    const loud=Math.sqrt(power/chunk.length)>Math.max(.009,detector.noise*3);
    if(loud){lastVoice=clock;if(draft&&draft.resumed===null)draft.resumed=clock;}
    detector.push(chunk);
    if(detector.active&&!draft&&detector.voiced>=rate*.16&&detector.quiet>=rate*.2){
      draft={at:clock,resumed:null,raw:encodeWav(detector.chunks,rate)};
    }
  }
  assert.ok(sourceTurns.length>=1&&sourceTurns.length<=3,'Unexpected number of detected turns');
  for(const row of sourceTurns)row.expected=sourceTurns.length===1?spec.expected:null;
  turns.push(...sourceTurns);
  sourceResults.push({case:spec.case,source_sha256:hash(bytes),detected_turns:sourceTurns.length,
    cancelled_drafts:sourceTurns.filter(r=>r.cancel_at_s!==null).length});
  if(!spec.challenge)pose=spec.pose||'unknown';
}
assert.ok(turns.length<=40);
fs.writeFileSync(path.join(folder,'fixtures.json'),JSON.stringify({
  scope:'Actual SpeechTurns at its current 650ms endpoint. First eligible 200ms pause, at most one draft per detected turn, cancelled on resumed energy. Synthetic PCM at equivalent 128-sample/48kHz intervals; no browser/device or semantic-endpoint claim.',
  detector_sha256:hash(fs.readFileSync(path.join(root,'local_app/web/microphone.mjs'))),sources:sourceResults,turns
},null,2)+'\n');
console.log(JSON.stringify({sources:sourceResults.length,detected_turns:turns.length,
  split_sources:sourceResults.filter(r=>r.detected_turns!==1),cancelled_drafts:turns.filter(r=>r.cancel_at_s!==null).length,
  output:folder}));
