// Same 350ms buffering, fMP4/WAV and speech synchronization as the working app.
import {streamingSource,synchronizeSpeech} from '/media-sync.mjs';
let token,context,analyser,controller,mediaURL;
const video=document.getElementById('video'),audio=new Audio();video.muted=true;
window.rtcBench={connected:false,transport:'mse',frames:[],audio:[],errors:[],turn:null};
const post=async(path,body={})=>{
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Local-Token':token},body:JSON.stringify(body)});
  const result=await response.json();if(!response.ok)throw Error(result.error);return result;
};
function event(target,name){return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{clean();reject(Error(name+' timed out'));},15000);
  const ok=()=>{clean();resolve();},bad=()=>{clean();reject(Error('Media failed'));};
  function clean(){clearTimeout(timer);target.removeEventListener(name,ok);target.removeEventListener('error',bad);}
  target.addEventListener(name,ok,{once:true});target.addEventListener('error',bad,{once:true});
});}
document.getElementById('connect').onclick=async()=>{
  context=new AudioContext();await context.resume();({token}=await (await fetch('/bootstrap')).json());
  analyser=context.createAnalyser();analyser.fftSize=512;
  context.createMediaElementSource(audio).connect(analyser);analyser.connect(context.destination);
  const frame=(_now,meta)=>{
    const at=performance.now(),turn=window.rtcBench.turn;
    window.rtcBench.frames.push({at,mediaTime:meta.mediaTime,marked:Boolean(turn)});
    if(turn&&turn.firstVideo===null)turn.firstVideo=at;
    if(turn&&meta.mediaTime>=.05&&turn.firstAdvancingVideo===null)turn.firstAdvancingVideo=at;
    video.requestVideoFrameCallback(frame);
  };video.requestVideoFrameCallback(frame);
  const samples=new Float32Array(512);
  const inspect=()=>{
    analyser.getFloatTimeDomainData(samples);let sum=0,peak=0;
    for(const value of samples){sum+=value*value;peak=Math.max(peak,Math.abs(value));}
    const rms=Math.sqrt(sum/samples.length),at=performance.now();window.rtcBench.audio.push({at,rms,peak});
    const turn=window.rtcBench.turn;if(turn&&rms>.006&&turn.firstAudio===null)turn.firstAudio=at;
    requestAnimationFrame(inspect);
  };inspect();window.rtcBench.connected=true;
};
async function play(info){
  const mime='video/mp4; codecs="avc1.42C01E, mp4a.40.2"';
  controller?.abort();controller=new AbortController();
  audio.src='/audio/'+info.index;audio.load();
  const release=synchronizeSpeech(video,audio,{signal:controller.signal,onBlocked:error=>window.rtcBench.errors.push(error.message)});
  if(mediaURL)URL.revokeObjectURL(mediaURL);
  const source=streamingSource(video,mime);if(!source)throw Error('MSE unavailable');
  mediaURL=URL.createObjectURL(source);video.src=mediaURL;await event(source,'sourceopen');
  const buffer=source.addSourceBuffer(mime),response=await fetch('/stream/'+info.index,{headers:{'X-Local-Token':token}});
  if(!response.ok)throw Error('Video stream failed');
  const reader=response.body.getReader();let started=false;
  try{
    for(;;){
      const {value,done}=await reader.read();if(done)break;
      const ready=event(buffer,'updateend');buffer.appendBuffer(value);await ready;
      if(!started&&video.buffered.length&&video.buffered.end(0)>=.35){started=true;await video.play();}
    }
    source.endOfStream();if(!started)await video.play();
    if(!video.ended)await event(video,'ended');
  }finally{reader.releaseLock();release();}
}
window.runRtcFixture=async fixture=>{
  const turn={started:performance.now(),firstVideo:null,firstAdvancingVideo:null,firstAudio:null};window.rtcBench.turn=turn;
  const info=await post('/run',{fixture});Object.assign(turn,info);
  play(info).catch(error=>window.rtcBench.errors.push(error.message));return info;
};
window.rtcResults=()=>post('/results');
window.finishRtc=async()=>{await post('/done');controller?.abort();return [];};
