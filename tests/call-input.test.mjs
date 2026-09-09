import test from 'node:test';
import assert from 'node:assert/strict';
import {CallInput} from '../local_app/web/call-input.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
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
