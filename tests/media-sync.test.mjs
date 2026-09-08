import {test} from 'node:test';
import assert from 'node:assert/strict';
import {synchronizeSpeech} from '../local_app/web/media-sync.mjs';
class Media extends EventTarget {
  paused=true; ended=false; currentTime=0; duration=5; readyState=4; playbackRate=1; plays=0;
  async play(){this.plays++;this.paused=false;this.dispatchEvent(new Event('playing'));}
  pause(){this.paused=true;this.dispatchEvent(new Event('pause'));}
  emit(name){this.dispatchEvent(new Event(name));}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
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
