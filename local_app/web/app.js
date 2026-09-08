import {synchronizeSpeech} from './media-sync.mjs';
import {Microphone} from './microphone.mjs';
const $=id=>document.getElementById(id);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let token="",ready=false,busy=false,active=null,submitting=false,pendingStop=false,connected=false;
let replyMode="video",scene="mira",hasVideo=false,playing=false,epoch=0,lastMedia=null,queue=[],abortMedia=null,objectURL=null;
let soundOn=true;
let historyOpen=false;
let viewMode='video',unread=0,micState='off',listenAfter=0;
const microphone=new Microphone({onTurn:raw=>submit('',raw,replyMode),canListen:()=>ready&&!busy&&!playing&&replyMode!=='text'&&performance.now()>listenAfter,
  onState:state=>{if(micState!==state){micState=state;controls();}}});
let lastStart=0,firstPlayed=null,stalls=0,firstBoot=true,provider="ollama",lastServerSeconds=null,waitingSince=null,waitingSeconds=0;
const sceneNames={mira:"Living room",garden:"Garden",cafe:"Café",fullbody:"Full-body garden"};
function notice(text="",error=false){$("notice").textContent=text;$("notice").className=error?"error":"";}
function controls(){
  $("send").disabled=!ready||busy;
  $("stop").hidden=!busy&&!playing;
  $("reset").disabled=submitting;
  const listening={off:'Mic off · type to talk',permission:'Allow microphone in your browser',hearing:'Hearing you…',processing:'Processing your words…',paused:'Listening resumes after the reply',listening:'Listening · speak naturally',disconnected:'Microphone disconnected'};
  $("call-state").textContent=playing?(firstPlayed===null?"Preparing playback…":"Mira is replying"):busy?"Preparing reply…":replyMode==='text'?'Text conversation':listening[micState];
  $("sound").textContent=soundOn?"Sound on":"Sound off";
  $("history-toggle").hidden=true;
  document.querySelector('.conversation').dataset.mode=viewMode;
  for(const mode of ['text','voice','video'])$('mode-'+mode).setAttribute('aria-pressed',String(viewMode===mode));
  for(const mode of ['voice','video'])$('mode-'+mode).dataset.active=replyMode===mode?'true':'false';
  $('mic').hidden=replyMode==='text';$('mic').disabled=!ready;
  $('mic').textContent=microphone.pending?'Cancel mic':microphone.enabled?'Mute mic':'Enable mic';
  $('mic').setAttribute('aria-pressed',String(microphone.enabled));
  $('end-call').hidden=replyMode==='text';$('sound').hidden=viewMode==='text'&&replyMode==='text';
  $('voice-view').hidden=viewMode!=='voice';$('voice-caption').textContent=$('call-state').textContent;
  if(viewMode==='voice')$('media-label').textContent='Voice call';
  $('replay').hidden=!lastMedia||(lastMedia.video?'video':'voice')!==viewMode||busy;
  $('unread').hidden=!unread;$('unread').textContent=String(unread);
  $('message').placeholder=viewMode==='text'?'Message Mira…':'Type to Mira during the call…';
  $('disclosure').textContent=viewMode==='text'?(replyMode==='text'?'Private local conversation':'Call stays active · return using the call tab'):'AI-generated '+(viewMode==='video'?'video':'voice')+' · Listening pauses during replies';
}
async function api(path,body){
  const response=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"X-Local-Token":token,...(body===undefined?{}:{"Content-Type":"application/json"})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
  const data=await response.json();
  if(!response.ok){if(response.status===403)connected=false;throw Error(data.error||"Request failed. Please retry.");}
  return data;
}
function bubble(text,role){
  $("chat").querySelector(".empty")?.remove();
  const box=document.createElement("div");box.className="bubble "+role;
  const content=document.createElement("span");content.textContent=text;box.append(content);$("chat").append(box);
  $("chat").scrollTop=$("chat").scrollHeight;
  return content;
}
function renderHistory(turns){$("chat").replaceChildren();for(const t of turns){bubble(t.user,"user");bubble(t.assistant,"assistant");if(t.message)bubble(t.message,'assistant sent-message');}}
function setScene(value){
  if(!sceneNames[value])return;
  if(value!==scene)$("held-frame").hidden=true;
  document.querySelector(".visual").dataset.scene=value;
  document.querySelector(".conversation").dataset.scene=value;
  document.querySelector(".conversation").dataset.history=historyOpen?"open":"closed";
  scene=value;$("portrait").src="/portrait/"+scene+".png";
  $("video").poster="/portrait/"+scene+".png";
  $("media-label").textContent=sceneNames[scene]+" · AI portrait";
}
function setAction(value="none"){document.querySelector(".visual").dataset.action=value||"none";}
function resetPlayback(holdFrame=false){
  const held=$("held-frame"),picture=$("video");
  if(holdFrame&&!picture.hidden&&picture.readyState>=2){
    held.width=picture.videoWidth;held.height=picture.videoHeight;
    held.getContext("2d").drawImage(picture,0,0);held.hidden=false;
  }else if(!holdFrame)held.hidden=true;
  epoch++;queue=[];playing=false;abortMedia?.abort();abortMedia=null;
  for(const media of [$("video"),$("audio")]){media.pause();media.removeAttribute("src");media.load();}
  if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
  $("video").hidden=true;$("resume").hidden=true;setScene(scene);controls();
}
function played(){
  if(!$("video").hidden)$("held-frame").hidden=true;
  if(waitingSince!==null){waitingSeconds+=(performance.now()-waitingSince)/1000;waitingSince=null;}
  if(firstPlayed===null){firstPlayed=(performance.now()-lastStart)/1000;updateMetrics();}
  $("resume").hidden=true;updateMetrics();controls();
}
function updateMetrics(){
  $("metrics").textContent=(firstPlayed===null?"Playback hasn't started.":"First playback: "+firstPlayed.toFixed(2)+"s from Send.")+" Buffer waits: "+stalls+" ("+waitingSeconds.toFixed(2)+"s)."+(lastServerSeconds===null?"":" Server completed: "+lastServerSeconds.toFixed(2)+"s.");
}
function waitEvent(target,name,signal,timeout=45000){
  return new Promise((resolve,reject)=>{
    let timer;
    const clear=()=>{clearTimeout(timer);target.removeEventListener(name,ok);target.removeEventListener("error",bad);signal?.removeEventListener("abort",cancel);};
    const ok=()=>{clear();resolve();},bad=()=>{clear();reject(Error("Media could not play. Try Replay."));},cancel=()=>{clear();reject(new DOMException("Stopped","AbortError"));};
    target.addEventListener(name,ok,{once:true});target.addEventListener("error",bad,{once:true});signal?.addEventListener("abort",cancel,{once:true});
    timer=setTimeout(()=>{clear();reject(Error("Playback timed out. Try Replay."));},timeout);
    if(signal?.aborted)cancel();
  });
}
async function attemptPlay(media){
  try{await media.play();}catch(error){if(error.name==="NotAllowedError"){$("resume").hidden=false;notice("Tap Play reply to enable sound.");}else throw error;}
}
async function playStream(item,media,signal){
  const mime='video/mp4; codecs="avc1.42C01E, mp4a.40.2"';
  if(!window.MediaSource||!MediaSource.isTypeSupported(mime))return false;
  const source=new MediaSource();objectURL=URL.createObjectURL(source);media.src=objectURL;
  await waitEvent(source,"sourceopen",signal,10000);
  const buffer=source.addSourceBuffer(mime);
  const response=await fetch(item.stream,{headers:{"X-Local-Token":token},signal});
  if(!response.ok)throw Error("Video connection failed. Try Replay.");
  const reader=response.body.getReader();let started=false;
  try{
    for(;;){
      const {value,done}=await reader.read();if(done)break;
      const appended=waitEvent(buffer,"updateend",signal,10000);buffer.appendBuffer(value);await appended;
      if(!started && media.buffered.length && media.buffered.end(0)>=.35){started=true;await attemptPlay(media);}
    }
    if(source.readyState==="open")source.endOfStream();
    if(!started)await attemptPlay(media);
    return true;
  }finally{reader.releaseLock();}
}
async function drain(){
  if(playing||!queue.length)return;
  playing=true;controls();const mine=epoch;
  while(queue.length&&mine===epoch){
    const item=queue.shift();lastMedia=item;$("replay").hidden=false;
    const media=item.video?$("video"):$("audio");
    const speech=item.video?$("audio"):media;
    if(item.video){media.hidden=false;media.muted=true;$("media-label").textContent=sceneNames[scene]+" · Generated video";}
    speech.muted=!soundOn;speech.volume=1;
    const controller=new AbortController();abortMedia=controller;
    let releaseSpeech=()=>{};
    if(item.video&&item.audio){
      speech.src=item.audio;speech.load();
      releaseSpeech=synchronizeSpeech(media,speech,{signal:controller.signal,onBlocked:error=>{
        $("resume").hidden=false;
        notice(error.name==="NotAllowedError"?"Tap Play reply to enable voice.":"Voice playback failed. Try Replay or Test sound.",true);
      }});
    }
    media.onplaying=played;
    media.onwaiting=()=>{if(firstPlayed!==null&&waitingSince===null){stalls++;waitingSince=performance.now();updateMetrics();}};
    media.onended=()=>{if(waitingSince!==null){waitingSeconds+=(performance.now()-waitingSince)/1000;waitingSince=null;}updateMetrics();};
    try{
      if(item.stream){
        const supported=await playStream(item,media,controller.signal);
        if(!supported){
          notice("This browser needs the completed video. Preparing it…");
          while(active&&mine===epoch){await sleep(150);if(!active)break;}
          if(mine!==epoch)break;media.src=item.video;await attemptPlay(media);
        }
      }else{media.src=item.video||item.audio;await attemptPlay(media);}
      if(!media.ended)await waitEvent(media,"ended",controller.signal,Math.max(45000,(item.duration_s+20)*1000));
      if(item.video&&item.audio&&!speech.ended&&!speech.paused)
        await waitEvent(speech,"ended",controller.signal,10000);
    }catch(error){
      if(mine===epoch&&error.name!=="AbortError"){notice(error.message,true);$("resume").hidden=false;}
    }
    releaseSpeech();
    if(mine===epoch&&objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
  }
  if(mine===epoch){playing=false;abortMedia=null;listenAfter=performance.now()+450;controls();}
}
$("resume").addEventListener("click",async()=>{
  const media=$("video").hidden?$("audio"):$("video");
  try{await media.play();$("resume").hidden=true;}catch{if(lastMedia){resetPlayback();queue.push({...lastMedia,stream:null});drain();}}
});
$("replay").addEventListener("click",()=>{if(lastMedia&&!busy){const item={...lastMedia,stream:null};resetPlayback();queue.push(item);drain();}});
async function follow(key,node){
  active=key;let replyNode=null,consumed=0,shownPortrait=false,shownMessage=false;
  try{
    for(;;){
      const job=await api("/api/jobs/"+key);if(active!==key)return;
      if(job.user)node.textContent=job.user;
      if(!pendingStop&&job.scene&&scene!==job.scene){setScene(job.scene);$("video").hidden=true;}
      if(job.action)setAction(job.action);
      if(job.text){replyNode??=bubble("","assistant");if(replyNode.textContent!==job.text){replyNode.textContent=job.text;$("chat").scrollTop=$("chat").scrollHeight;}}
      if(job.state==='done'&&job.message&&!shownMessage){bubble(job.message,'assistant sent-message');shownMessage=true;if(viewMode!=='text')unread++;controls();}
      if(job.portrait&&!shownPortrait&&replyNode){const image=document.createElement("img");image.src=job.portrait;image.alt="Mira in the "+sceneNames[job.scene].toLowerCase();replyNode.parentElement.append(image);shownPortrait=true;$("chat").scrollTop=$("chat").scrollHeight;}
      while(!pendingStop&&consumed<job.chunks.length){queue.push(job.chunks[consumed++]);drain();}
      if(job.state==="thinking")notice("Mira is thinking…");
      else if(job.state==="transcribing")notice("Listening to your message…");
      else if(job.state==="rendering"&&!playing)notice("Connecting the picture…");
      else if(job.state==="speaking"&&!playing)notice("Preparing your reply…");
      if(["done","failed","cancelled"].includes(job.state)){
        if(job.state==="failed"&&job.error_code==="no_speech"){node.parentElement.remove();notice("No speech detected. Speak again or type.");}
        else if(job.state==="failed"){notice(job.error,true);if(!replyNode)bubble("That reply couldn't finish. Please try again.","assistant");}
        else if(job.state==="cancelled")notice("Stopped. You can talk or type now.");
        else if($("resume").hidden){notice(job.remembered?.length?"Saved what you shared. You can review it in Memory.":"");}
        lastServerSeconds=job.metrics.total_s??null;updateMetrics();
        break;
      }
      await sleep(100);
    }
  }catch(error){notice(error.message,true);}
  finally{if(active===key){active=null;busy=false;controls();}}
}
async function submit(text,raw=null,inputMode=null){
  if(busy||!ready||(!raw&&!text.trim()))return;
  resetPlayback(true);lastStart=performance.now();firstPlayed=null;stalls=0;waitingSince=null;waitingSeconds=0;lastServerSeconds=null;updateMetrics();
  pendingStop=false;submitting=true;busy=true;controls();
  const node=bubble(raw?"Listening…":text,"user");
  if(!raw)$("message").value="";
  notice(raw?"Listening to your message…":"Mira is thinking…");
  try{
    let data;
    const mode=inputMode||viewMode;
    if(raw){
      const response=await fetch("/api/audio",{method:"POST",headers:{"Content-Type":"audio/wav","X-Local-Token":token,"X-Reply-Mode":mode,"X-Scene":"auto"},body:raw,signal:AbortSignal.timeout(10000)});
      data=await response.json();if(!response.ok)throw Error(data.error);
    }else data=await api("/api/turn",{text,mode,scene:"auto"});
    submitting=false;active=data.id;if(pendingStop)await api("/api/cancel",{id:data.id});
    await follow(data.id,node);
  }catch(error){submitting=false;busy=false;controls();notice(error.message,true);if(!raw)$("message").value=text;}
}
$("composer").addEventListener("submit",e=>{e.preventDefault();submit($("message").value);});
$("message").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();submit($("message").value);}});
async function interrupt(){
  pendingStop=true;
  if(active||submitting)lastMedia=null;
  resetPlayback(true);
  if(submitting){pendingStop=true;return;}
  if(active){try{await api("/api/cancel",{id:active});notice("Stopping…");}catch(error){notice(error.message,true);}}
  else notice("Reply stopped. Type your next message.");
}
$("stop").addEventListener("click",interrupt);
$('mic').addEventListener('click',async()=>{
  if(microphone.enabled||microphone.pending){microphone.stop();return;}
  try{await microphone.start();}catch(error){notice(error.message,true);}controls();
});
for(const mode of ['text','voice','video'])$('mode-'+mode).addEventListener('click',async()=>{
  if(mode!=='text'&&replyMode!==mode){
    microphone.stop();await interrupt();replyMode=mode;
  }
  viewMode=mode;if(mode==='text')unread=0;controls();notice();
  if(mode==='text')$('chat').scrollTop=$('chat').scrollHeight;
});
$('end-call').addEventListener('click',async()=>{microphone.stop();replyMode='text';viewMode='text';await interrupt();controls();notice('Call ended. Your messages are here.');});
$("sound").addEventListener("click",()=>{soundOn=!soundOn;$("video").muted=true;$("audio").muted=!soundOn;controls();});
$("history-toggle").addEventListener("click",()=>{
  historyOpen=!historyOpen;
  document.querySelector(".conversation").dataset.history=historyOpen?"open":"closed";
  $("history-toggle").textContent=historyOpen?"Hide messages":"Show messages";
  $("history-toggle").setAttribute("aria-expanded",String(historyOpen));
  $("chat").scrollTop=$("chat").scrollHeight;
});
let soundTestContext;
$("test-sound").addEventListener("click",async()=>{
  try{
    soundTestContext??=new AudioContext();await soundTestContext.resume();
    const tone=soundTestContext.createOscillator(),gain=soundTestContext.createGain();
    tone.frequency.value=440;gain.gain.value=.08;tone.connect(gain);gain.connect(soundTestContext.destination);
    tone.start();tone.stop(soundTestContext.currentTime+.4);
    notice("Test tone sent. If you hear nothing, check this browser's sound permission and your Windows output device.");
  }catch(error){notice("Sound test failed: "+error.message,true);}
});
function renderFacts(facts=[]){
  $("facts").replaceChildren();
  if(!facts.length){const p=document.createElement("p");p.className="no-facts";p.textContent="No facts saved yet."; $("facts").append(p);}
  for(const fact of facts){
    const row=document.createElement("div");row.className="fact";const text=document.createElement("span");text.textContent=fact.quote;
    const button=document.createElement("button");button.className="quiet";button.textContent="Forget";button.setAttribute("aria-label","Forget "+fact.key.replaceAll("_"," "));
    button.addEventListener("click",async()=>{try{await api("/api/facts/delete",{key:fact.key});row.remove();}catch(error){notice(error.message,true);}});
    row.append(text,button);$("facts").append(row);
  }
}
$("memory-toggle").addEventListener("click",async()=>{
  try{const data=await api("/api/status");$("memory").value=data.memory;renderFacts(data.facts);$("settings").showModal();}catch(error){notice(error.message,true);}
});
$("close-settings").addEventListener("click",()=>$("settings").close());
$("save-memory").addEventListener("click",async()=>{try{await api("/api/memory",{memory:$("memory").value});$("settings").close();notice("Notes saved.");}catch(error){notice(error.message,true);}});
$("reset").addEventListener("click",async()=>{
  if(!confirm("Erase this local conversation, saved facts and generated replies? Prepared pictures remain."))return;
  try{microphone.stop();replyMode=viewMode="text";unread=0;resetPlayback();await api("/api/reset",{});active=null;busy=false;lastMedia=null;$("replay").hidden=true;$("chat").replaceChildren();$("memory").value="";renderFacts();$("settings").close();setScene("mira");notice("Conversation and memory cleared.");controls();}catch(error){notice(error.message,true);}
});
window.addEventListener("pagehide",()=>{microphone.stop();abortMedia?.abort();});
async function boot(){
  for(;;){
    try{
      if(!connected){
        const data=await api("/api/bootstrap");
        const restarted=token&&token!==data.token;token=data.token;connected=true;
        if(firstBoot||restarted){renderHistory(data.turns);setScene(data.scene||"mira");firstBoot=false;}
        if(restarted){resetPlayback();active=null;busy=false;notice("Reconnected. Send your message again if the last reply was interrupted.");}
      }
      const state=await api("/api/status");ready=state.ready;hasVideo=state.visual_loaded;provider=state.provider;
      if(state.app_version!=="0.2"){ready=false;$("connection").textContent="Server update needed";notice("Restart the local server to finish this update.",true);controls();await sleep(1500);continue;}
      if(!active&&!submitting)busy=state.busy;
      $("connection").textContent=state.error?"Models unavailable":!ready?"Preparing Mira…":provider==="ollama"?"On your computer":"Hosted conversation · local video";
      $("provider-note").textContent=provider==="ollama"?"Qwen dialogue, voice and video run on this PC.":"Conversation, recent context and saved notes go to "+provider+". Voice and video stay on this PC.";
      if(state.error)notice(state.error,true);else if(state.visual_error)notice(state.visual_error,true);
      controls();
    }catch(error){connected=false;ready=false;$("connection").textContent="Reconnecting…";notice("Connection lost. Retrying automatically; your draft stays here.",true);controls();}
    await sleep(1500);
  }
}
boot();
