import test from 'node:test';
import assert from 'node:assert/strict';
import {CallInput,speechAccess,continueSpeech} from '../local_app/web/call-input.mjs';
import {encodeWav} from '../local_app/web/microphone.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('speech during silent reply preparation can cancel before playback, even without AEC',()=>{
  const state={ready:true,enabled:true,mode:'video',busy:true,playing:false,stopping:false,submitting:false,echoCancellation:false,settled:true};
  assert.deepEqual(speechAccess(state),{canListen:true,canInterrupt:true});
  for(const change of [{playing:true},{settled:false},{stopping:true},{submitting:true},{enabled:false},{mode:'text'},{ready:false}])
    assert.deepEqual(speechAccess({...state,...change}),{canListen:false,canInterrupt:false});
  assert.deepEqual(speechAccess({...state,playing:true,echoCancellation:true}),{canListen:true,canInterrupt:true});
  assert.deepEqual(speechAccess({...state,settled:false,echoCancellation:true}),{canListen:false,canInterrupt:false});
  assert.deepEqual(speechAccess({...state,busy:false}),{canListen:true,canInterrupt:false});
});
test('an interrupting utterance survives cleanup but never survives mute or call end',()=>{
  const state={ready:true,enabled:true,mode:'voice',busy:true,playing:false,stopping:true,submitting:false,echoCancellation:false,settled:false,capturing:true};
  assert.deepEqual(speechAccess(state),{canListen:true,canInterrupt:false});
  for(const change of [{enabled:false},{mode:'text'},{ready:false}])
    assert.deepEqual(speechAccess({...state,...change}),{canListen:false,canInterrupt:false});
});
function setup(extra={}){
  const state={stamp:'call1:mic1:video',canInterrupt:true,busy:true},sent=[],errors=[];
  let stopCount=0;
  const input=new CallInput({state:()=>state,stop:()=>{stopCount++;},submit:raw=>sent.push(raw),onError:e=>errors.push(e.message),...extra});
  return {state,sent,errors,input,get stopCount(){return stopCount;}};
}
test('one interruption retains the utterance until cancellation and busy cleanup finish',async()=>{
  let finishStop;const rig=setup({stop:()=>new Promise(resolve=>finishStop=resolve)});
  rig.input.speech();assert.equal(rig.input.capturing(),true);
  const audio=new Uint8Array([1,2,3]),pending=rig.input.turn(audio);
  assert.equal(rig.input.capturing(),false);assert.equal(rig.sent.length,0);
  rig.input.speech();await rig.input.turn(new Uint8Array([9]));assert.equal(rig.sent.length,0);
  finishStop();await tick();assert.equal(rig.sent.length,0);
  rig.state.busy=false;await pending;
  assert.deepEqual(rig.sent,[audio]);assert.equal(rig.input.pending,null);
});
test('end, mute, or mode generation change drops queued audio',async()=>{
  for(const change of ['stamp','reset']){
    let finishStop;const rig=setup({stop:()=>new Promise(resolve=>finishStop=resolve)});
    rig.input.speech();const pending=rig.input.turn(new Uint8Array([1]));
    if(change==='stamp')rig.state.stamp='call2:mic2:voice';else rig.input.reset();
    rig.state.busy=false;finishStop();await pending;
    assert.equal(rig.sent.length,0);assert.equal(rig.input.pending,null);
  }
});
test('cleanup timeout and rejected cancellation never start another render',async()=>{
  let time=0;const rig=setup({now:()=>time,wait:async()=>{time+=1000;}});
  rig.input.speech();await rig.input.turn(new Uint8Array([1]));
  assert.equal(rig.sent.length,0);assert.equal(rig.errors.length,1);assert.equal(rig.input.pending,null);
  const failed=setup({stop:async()=>false});failed.input.speech();failed.state.busy=false;
  await failed.input.turn(new Uint8Array([1]));assert.equal(failed.sent.length,0);assert.equal(failed.errors.length,1);
});
test('normal speech passes through; disabled interruption never calls stop',async()=>{
  const rig=setup();rig.state.canInterrupt=false;rig.state.busy=false;
  rig.input.speech();assert.equal(rig.stopCount,0);
  await rig.input.turn(new Uint8Array([1]));assert.equal(rig.sent.length,1);
  rig.state.canInterrupt=true;rig.input.speech();rig.input.speech();assert.equal(rig.stopCount,1);
  rig.state.stamp='new';assert.equal(rig.input.capturing(),false);
});
test('short completed words can interrupt without an earlier onset callback',async()=>{
  const rig=setup();rig.state.busy=false;
  await rig.input.turn(new Uint8Array([1]));
  assert.equal(rig.stopCount,1);assert.equal(rig.sent.length,1);assert.equal(rig.input.pending,null);
});
test('an explicit typed command interrupts without microphone echo cancellation',async()=>{
  const rig=setup();rig.state.canInterrupt=false;rig.state.busy=false;
  const command={text:'Please step back.',mode:'video'};
  await rig.input.turn(command,{interrupt:true});
  assert.equal(rig.stopCount,1);assert.deepEqual(rig.sent,[command]);
});

test('a resumed sentence before reply playback preserves both PCM segments in order',async()=>{
  const rig=setup();rig.state.canInterrupt=false;rig.state.busy=false;
  const before={raw:encodeWav([new Float32Array(1600).fill(.1)],16000),mode:'video'};
  const after={raw:encodeWav([new Float32Array(2400).fill(-.2)],16000),mode:'video'};
  await rig.input.turn(before);
  rig.state.canInterrupt=true;rig.state.canContinue=true;rig.state.busy=true;
  rig.input.speech();rig.state.busy=false;await rig.input.turn(after);
  const combined=rig.sent[1];assert.equal(combined.raw.byteLength,8044);
  assert.equal(new DataView(combined.raw).getInt16(44,true),3276);
  assert.equal(new DataView(combined.raw).getInt16(44+3200,true),-6553);
  assert.equal(new DataView(combined.raw).getUint32(40,true),8000);
});
test('playback interruptions, typed replacements and new call generations never prepend old audio',async()=>{
  for(const change of ['playback','typed','generation']){
    const rig=setup();rig.state.canInterrupt=false;rig.state.busy=false;
    await rig.input.turn({raw:encodeWav([new Float32Array(1600)],16000),mode:'video'});
    rig.state.canInterrupt=true;rig.state.canContinue=change!=='playback';
    if(change==='generation')rig.state.stamp='new';
    const next=change==='typed'?{text:'Stop.',mode:'video'}:{raw:encodeWav([new Float32Array(2400)],16000),mode:'video'};
    await rig.input.turn(next,{interrupt:change==='typed'});
    assert.equal(rig.sent[1],next);
  }
});
test('audio continuation rejects invalid formats, changed devices and recordings over 30 seconds',()=>{
  const input=(seconds,rate=16000)=>({raw:encodeWav([new Float32Array(seconds*rate)],rate),mode:'video'});
  assert.throws(()=>continueSpeech(input(1),input(1,48000)),/microphone changed/);
  assert.throws(()=>continueSpeech(input(20),input(11)),/too long/);
  const bad=input(1);new DataView(bad.raw).setUint32(40,999,true);
  assert.throws(()=>continueSpeech(input(1),bad),/Could not combine/);
  const changedMode=input(1);changedMode.mode='voice';assert.equal(continueSpeech(input(1),changedMode),changedMode);
});
test('a failed audio combination reports recovery and never submits the truncated remainder',async()=>{
  const rig=setup({combine:()=>{throw Error('Please repeat your sentence.');}});
  rig.state.canInterrupt=false;rig.state.busy=false;await rig.input.turn({raw:'old'});
  rig.state.canInterrupt=true;rig.state.canContinue=true;
  await rig.input.turn({raw:'new'});
  assert.equal(rig.sent.length,1);assert.deepEqual(rig.errors,['Please repeat your sentence.']);
  assert.equal(rig.input.pending,null);
});
