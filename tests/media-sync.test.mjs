import {test} from 'node:test';
import assert from 'node:assert/strict';
import {synchronizeSpeech, streamingSource} from '../local_app/web/media-sync.mjs';
test('streaming uses desktop MSE when supported and iPhone managed source otherwise',()=>{
  const media={disableRemotePlayback:false};
  class Desktop{static isTypeSupported(mime){return mime==='video/test';}}
  class Managed{static isTypeSupported(mime){return mime==='video/test';}
    constructor(){assert.equal(media.disableRemotePlayback,true);}}
  assert.ok(streamingSource(media,'video/test',{MediaSource:Desktop,ManagedMediaSource:Managed}) instanceof Desktop);
  assert.equal(media.disableRemotePlayback,false);
  assert.ok(streamingSource(media,'video/test',{ManagedMediaSource:Managed}) instanceof Managed);
  assert.equal(streamingSource(media,'video/unsupported',{MediaSource:Desktop,ManagedMediaSource:Managed}),null);
  assert.equal(streamingSource(media,'video/test',{}),null);
});
class Media extends EventTarget {
  paused=true; ended=false; currentTime=0; duration=5; readyState=4; playbackRate=1; plays=0;
  async play(){this.plays++;this.paused=false;this.dispatchEvent(new Event('playing'));}
  pause(){this.paused=true;this.dispatchEvent(new Event('pause'));}
  emit(name){this.dispatchEvent(new Event(name));}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('silent gesture tail does not repeatedly seek an ended speech track',()=>{
  const video=new Media(),audio=new Media();let position=audio.duration,seeks=0;
  Object.defineProperty(audio,'currentTime',{get:()=>position,set:value=>{position=value;seeks++;}});
  audio.ended=true;
  const release=synchronizeSpeech(video,audio);
  for(const time of [5.3,5.6,6,7]){video.currentTime=time;video.emit('timeupdate');}
  assert.equal(seeks,0);
  video.currentTime=2;video.emit('seeking');
  assert.equal(position,2);assert.equal(seeks,1);
  release();
});
test('speech starts on first video playback, pauses on stalls and resynchronizes',async()=>{
  const video=new Media(),audio=new Media();const release=synchronizeSpeech(video,audio);
  assert.equal(audio.plays,0);
  await video.play();await tick();assert.equal(audio.plays,1);assert.equal(audio.paused,false);
  video.emit('waiting');assert.equal(audio.paused,true);
  video.currentTime=1.8;video.emit('playing');await tick();
  assert.equal(audio.currentTime,1.8);assert.equal(audio.paused,false);
  video.pause();assert.equal(audio.paused,true);
  release();await video.play();assert.equal(audio.paused,true);
});
test('blocked speech pauses picture and cancellation removes listeners',async()=>{
  const video=new Media(),audio=new Media(),controller=new AbortController();let blocked=0;
  audio.play=async()=>{throw new DOMException('gesture needed','NotAllowedError');};
  synchronizeSpeech(video,audio,{signal:controller.signal,onBlocked:()=>blocked++});
  await video.play();await tick();assert.equal(video.paused,true);assert.equal(blocked,1);
  controller.abort();await video.play();await tick();assert.equal(blocked,1);
});
test('late audio play completion cannot restart speech after interruption',async()=>{
  const video=new Media(),audio=new Media(),controller=new AbortController();let finish;
  audio.play=()=>new Promise(resolve=>{finish=()=>{audio.paused=false;resolve();};});
  synchronizeSpeech(video,audio,{signal:controller.signal});
  await video.play();controller.abort();finish();await tick();assert.equal(audio.paused,true);
});
