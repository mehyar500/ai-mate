import test from 'node:test';
import assert from 'node:assert/strict';
import {SpeechTurns,encodeWav,Microphone} from '../local_app/web/microphone.mjs';

test('WAV is mono PCM16 with bounded/clipped samples',()=>{
  const wav=new DataView(encodeWav([new Float32Array([-2,0,.5,2])],48000));
  assert.equal(wav.getUint32(24,true),48000);assert.equal(wav.getUint16(22,true),1);
  assert.equal(wav.getUint32(40,true),8);assert.equal(wav.getInt16(44,true),-32768);assert.equal(wav.getInt16(50,true),32767);
});
test('silence and clicks do not submit; a spoken turn submits once after a pause',()=>{
  const turns=[],vad=new SpeechTurns(16000,raw=>turns.push(raw));
  const silence=new Float32Array(160),voice=new Float32Array(160).fill(.1);
  for(let i=0;i<100;i++)vad.push(silence);assert.equal(turns.length,0);
  vad.push(voice);for(let i=0;i<70;i++)vad.push(silence);assert.equal(turns.length,0);
  for(let i=0;i<60;i++)vad.push(voice);for(let i=0;i<64;i++)vad.push(silence);assert.equal(turns.length,0);
  vad.push(silence);assert.equal(turns.length,1);
  for(let i=0;i<100;i++)vad.push(silence);assert.equal(turns.length,1);
});
test('reset discards partial speech and long speech is bounded below server limit',()=>{
  const turns=[],vad=new SpeechTurns(16000,raw=>turns.push(raw)),voice=new Float32Array(160).fill(.1);
  for(let i=0;i<30;i++)vad.push(voice);vad.reset();for(let i=0;i<70;i++)vad.push(new Float32Array(160));assert.equal(turns.length,0);
  for(let i=0;i<2600;i++)vad.push(voice);assert.equal(turns.length,1);
  assert.ok((turns[0].byteLength-44)/32000<=25.01);
});
test('speech onset fires once after 240ms and preserves the first samples',()=>{
  const turns=[];let onsets=0;const vad=new SpeechTurns(16000,raw=>turns.push(raw),()=>onsets++);
  const voice=new Float32Array(160).fill(.1),silence=new Float32Array(160);
  for(let i=0;i<23;i++)vad.push(voice);assert.equal(onsets,0);
  vad.push(voice);assert.equal(onsets,1);
  for(let i=0;i<35;i++)vad.push(voice);assert.equal(onsets,1);
  for(let i=0;i<65;i++)vad.push(silence);assert.equal(turns.length,1);
  assert.equal(new DataView(turns[0]).getInt16(44,true),3276);
});
test('ending a call during permission prompt stops a late microphone stream',async()=>{
  const original=Object.getOwnPropertyDescriptor(globalThis,'navigator'),secure=globalThis.isSecureContext;
  let grant,stopped=0;
  Object.defineProperty(globalThis,'navigator',{value:{mediaDevices:{getUserMedia:()=>new Promise(resolve=>grant=resolve)}},configurable:true});
  globalThis.isSecureContext=true;
  try{
    const mic=new Microphone({onTurn:()=>assert.fail(),onState:()=>{},canListen:()=>true});
    const pending=mic.start();mic.stop();grant({getTracks:()=>[{stop:()=>stopped++}]});await pending;
    assert.equal(stopped,1);assert.equal(mic.enabled,false);assert.equal(mic.pending,false);
  }finally{if(original)Object.defineProperty(globalThis,'navigator',original);else delete globalThis.navigator;globalThis.isSecureContext=secure;}
});
test('interruption eligibility uses reported local echo cancellation, not requested constraints',async()=>{
  const saved=Object.fromEntries(['navigator','AudioContext','AudioWorkletNode','isSecureContext'].map(k=>[k,Object.getOwnPropertyDescriptor(globalThis,k)]));
  class Context{sampleRate=16000;state='running';audioWorklet={addModule:async()=>{}};
    async resume(){} async close(){this.state='closed';}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}}
  class Worklet{port={};connect(){}disconnect(){}}
  Object.defineProperty(globalThis,'AudioContext',{value:Context,configurable:true});
  Object.defineProperty(globalThis,'AudioWorkletNode',{value:Worklet,configurable:true});
  globalThis.isSecureContext=true;
  try{
    for(const setting of [true,'all',false,'remote-only',undefined]){
      const track={stop(){},getSettings:()=>({echoCancellation:setting})};
      Object.defineProperty(globalThis,'navigator',{value:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[track],getAudioTracks:()=>[track]})}},configurable:true});
      const mic=new Microphone({onTurn(){},onState(){},canListen:()=>true});
      await mic.start();assert.equal(mic.echoCancellation,[true,'all'].includes(setting));
      mic.stop();assert.equal(mic.echoCancellation,false);
    }
  }finally{for(const [k,descriptor] of Object.entries(saved)){if(descriptor)Object.defineProperty(globalThis,k,descriptor);else delete globalThis[k];}}
});
