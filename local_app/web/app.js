import {synchronizeSpeech, streamingSource} from './media-sync.mjs';
import {Microphone} from './microphone.mjs';
import {CallInput} from './call-input.mjs';
const $=id=>document.getElementById(id);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let token="",ready=false,busy=false,active=null,submitting=false,pendingStop=false,connected=false;
let replyMode="text",scene="mira",hasVideo=false,playing=false,epoch=0,lastMedia=null,queue=[],abortMedia=null,objectURL=null;
let idleURL=null,idleFailed=false,idleSuppressed=false;
let nextIdleURL=undefined,pictureStarted=false,motionRequested=false;
let stopping=false,displayedPlayback=null,frameCallback=null;
let callInputOpen=false;
function settleIdle(){
  if(nextIdleURL!==undefined){idleURL=nextIdleURL;nextIdleURL=undefined;idleSuppressed=!idleURL;}
  pictureStarted=false;
}
function idlePresence(){
  const video=$('idle-video');
  const visible=ready&&connected&&!document.hidden&&viewMode==='video'&&replyMode==='video'&&scene==='fullbody'&&idleURL&&!idleFailed&&!idleSuppressed&&!pictureStarted;
  if(!visible){video.pause();video.hidden=true;return;}
  if(video.getAttribute('src')!==idleURL)video.src=idleURL;
  video.muted=true;video.hidden=false;$('held-frame').hidden=true;
  if(video.paused)video.play().then(()=>{if(video.hidden||document.hidden)video.pause();}).catch(()=>{if(!video.hidden)idleFailed=true;video.hidden=true;});
  $('media-label').textContent=(idleURL.includes('/near.')?'Garden close view':'Full-body garden')+' · Prepared listening loop';
}
$('idle-video').addEventListener('error',()=>{idleFailed=true;$('idle-video').hidden=true;});
document.addEventListener('visibilitychange',idlePresence);
let historyOpen=false;
let viewMode='video',unread=0,micState='off',listenAfter=0,callRequest=0;
let captionText='';
function updateCaptions(){
  $('captions').textContent=captionText;
  $('captions').hidden=viewMode==='text'||!$('show-captions').checked||!captionText;
}
$('show-captions').addEventListener('change',updateCaptions);
const callInput=new CallInput({
  state:()=>({stamp:callRequest+':'+microphone.generation+':'+replyMode,
    canInterrupt:ready&&microphone.enabled&&microphone.echoCancellation&&playing&&!stopping,
    busy:busy||stopping||submitting}),
  stop:()=>interrupt(),submit:input=>submit(input.text||'',input.raw||null,input.mode,input.draftId),
  onError:error=>notice(error.message,true)
});
const microphone=new Microphone({onTurn:raw=>callInput.turn({raw,mode:replyMode}),onSpeech:()=>callInput.speech(),
  canListen:()=>ready&&replyMode!=='text'&&(callInput.capturing()||
    (!stopping&&!submitting&&((playing&&microphone.echoCancellation)||(!busy&&!playing&&performance.now()>listenAfter)))),
  onState:state=>{if(state==='off')callInput.reset();if(micState!==state){micState=state;controls();}}});
let lastStart=0,firstPlayed=null,stalls=0,firstBoot=true,provider="ollama",lastServerSeconds=null,waitingSince=null,waitingSeconds=0;
let partEndedAt=null,phraseGapSeconds=0;
const sceneNames={mira:"Living room",garden:"Garden",cafe:"Café",fullbody:"Full-body garden"};
function notice(text="",error=false){$("notice").textContent=text;$("notice").className=error?"error":"";}
function controls(){
  $("send").disabled=!ready||busy||stopping;
  $("stop").hidden=viewMode==='text'||(!busy&&!playing);
  $("reset").disabled=submitting;
  const listening={off:'Microphone muted',permission:'Allow microphone in your browser',hearing:'Hearing you…',processing:'Processing your words…',paused:'Mira is replying',listening:'Listening',disconnected:'Microphone disconnected'};
  $("call-state").textContent=replyMode!=='text'&&micState==='hearing'?'Hearing you…':playing?(firstPlayed===null?"Preparing playback…":"Mira is replying"):busy?"Preparing reply…":replyMode==='text'?(viewMode==='text'?'Text conversation':'Ready when you are'):listening[micState];
  $("history-toggle").hidden=true;
  document.querySelector('.conversation').dataset.mode=viewMode;
  for(const mode of ['text','voice','video'])$('mode-'+mode).setAttribute('aria-pressed',String(viewMode===mode));
  for(const mode of ['voice','video'])$('mode-'+mode).dataset.active=replyMode===mode?'true':'false';
  $('mic').hidden=viewMode==='text'||replyMode==='text';$('mic').disabled=!ready;
  const micLabel=microphone.pending?'Cancel microphone request':microphone.enabled?'Mute microphone':'Unmute microphone';
  $('mic').setAttribute('aria-label',micLabel);$('mic').title=micLabel;
  $('mic').setAttribute('aria-pressed',String(!microphone.enabled));
  $('mic').dataset.muted=String(!microphone.enabled);
  $('end-call').hidden=viewMode==='text'||replyMode==='text';
  document.querySelector('.call-actions').hidden=replyMode==='text';
  $('join-call').hidden=viewMode==='text'||replyMode!=='text';$('join-call').disabled=!ready;
  const joinLabel=ready?'Call Mira':connected?'Getting ready…':'Connecting…';
  $('join-call').querySelector('span').textContent=joinLabel;
  $('join-call').setAttribute('aria-label',joinLabel);$('join-call').title=joinLabel;
  $('composer').hidden=viewMode!=='text';
  const showCallInput=viewMode!=='text'&&replyMode!=='text';
  $('call-type').hidden=!showCallInput;
  $('call-type').setAttribute('aria-expanded',String(showCallInput&&callInputOpen));
  $('call-composer').hidden=!showCallInput||!callInputOpen;
  $('call-send').disabled=!ready||!showCallInput||stopping||submitting||Boolean(callInput.pending)||!$('call-message').value.trim();
  $('voice-view').hidden=viewMode!=='voice';$('voice-caption').textContent=$('call-state').textContent;
  $('active-call').hidden=viewMode!=='text'||replyMode==='text';
  $('active-call-title').textContent=(replyMode==='video'?'Video':'Voice')+' call active';
  $('active-call-status').textContent=$('call-state').textContent;
  $('return-call').textContent='Return to '+(replyMode==='video'?'video':'voice')+' call';
  if(viewMode==='voice')$('media-label').textContent='Voice call';
  $('replay').hidden=true;
  $('unread').hidden=!unread;$('unread').textContent=String(unread);
  $('message').placeholder='Message Mira…';
  $('disclosure').hidden=viewMode!=='text';
  $('disclosure').textContent=replyMode==='text'?'Private conversation':'Call stays active';
  updateCaptions();
  idlePresence();
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
  if(value!==scene){$("held-frame").hidden=true;idleSuppressed=false;}
  document.querySelector(".visual").dataset.scene=value;
  document.querySelector(".conversation").dataset.scene=value;
  document.querySelector(".conversation").dataset.history=historyOpen?"open":"closed";
  scene=value;$("portrait").src="/portrait/"+scene+".png";
  $("video").poster="/portrait/"+scene+".png";
  $("media-label").textContent=sceneNames[scene]+" · AI portrait";
}
function setAction(value="none"){document.querySelector(".visual").dataset.action=value||"none";}
function holdPicture(){
  const held=$("held-frame"),picture=$("video");
  if(!picture.hidden&&picture.readyState>=2&&picture.videoWidth&&picture.videoHeight){
    try{
      held.width=picture.videoWidth;held.height=picture.videoHeight;
      held.getContext("2d").drawImage(picture,0,0);held.hidden=false;
    }catch{held.hidden=true;} // The reviewed portrait remains underneath on decoder failure.
  }
  picture.hidden=true;
}
function resetPlayback(holdFrame=false){
  if(frameCallback!==null){$('video').cancelVideoFrameCallback?.(frameCallback);frameCallback=null;}
  displayedPlayback=null;
  partEndedAt=null;phraseGapSeconds=0;
  captionText='';
  nextIdleURL=undefined;pictureStarted=false;motionRequested=false;
  if(holdFrame)holdPicture();else $("held-frame").hidden=true;
  epoch++;queue=[];playing=false;abortMedia?.abort();abortMedia=null;
  for(const media of [$("video"),$("audio")]){media.pause();media.removeAttribute("src");media.load();}
  if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
  $("video").hidden=true;$("resume").hidden=true;setScene(scene);controls();
}
function played(){
  if(partEndedAt!==null){phraseGapSeconds+=(performance.now()-partEndedAt)/1000;partEndedAt=null;}
  if(!$("video").hidden){pictureStarted=true;if(motionRequested)idleSuppressed=true;}
  $('idle-video').pause();$('idle-video').hidden=true;
  if(!$("video").hidden)$("held-frame").hidden=true;
  if(waitingSince!==null){waitingSeconds+=(performance.now()-waitingSince)/1000;waitingSince=null;}
  if(firstPlayed===null){firstPlayed=(performance.now()-lastStart)/1000;updateMetrics();}
  $("resume").hidden=true;if(!$("notice").classList.contains('error'))notice('');updateMetrics();controls();
}
function updateMetrics(){
  $("metrics").textContent=(firstPlayed===null?"Playback hasn't started.":"First playback: "+firstPlayed.toFixed(2)+"s from Send.")+" Buffer waits: "+stalls+" ("+waitingSeconds.toFixed(2)+"s). Between phrases: "+phraseGapSeconds.toFixed(2)+"s."+(lastServerSeconds===null?"":" Server completed: "+lastServerSeconds.toFixed(2)+"s.");
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
  const source=streamingSource(media,mime);
  if(!source)return false;
  objectURL=URL.createObjectURL(source);media.src=objectURL;
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
    const item=queue.shift();lastMedia=item;
    const media=item.video?$("video"):$("audio");
    const speech=item.video?$("audio"):media;
    if(item.video){media.hidden=true;media.muted=true;}
    speech.muted=false;speech.volume=1;
    const controller=new AbortController();abortMedia=controller;
    let releaseSpeech=()=>{};
    let itemStarted=false;
    if(item.video&&item.audio){
      speech.src=item.audio;speech.load();
      releaseSpeech=synchronizeSpeech(media,speech,{signal:controller.signal,onBlocked:error=>{
        $("resume").hidden=false;
        notice(error.name==="NotAllowedError"?"Tap Play reply to enable voice.":"Voice playback failed. Try Replay or Test sound.",true);
      }});
    }
    media.onplaying=()=>{
      if(mine!==epoch)return;
      itemStarted=true;
      captionText=item.text||'';
      if(item.video){media.hidden=false;$("media-label").textContent=sceneNames[scene]+(item.prepared_motion?" · Prepared motion · live voice":" · Generated video");}
      if(item.video){
        displayedPlayback={id:item.jobId,playback:{index:item.index,time_s:media.currentTime}};
        const track=(_now,frame)=>{
          if(mine!==epoch||lastMedia!==item)return;
          displayedPlayback={id:item.jobId,playback:{index:item.index,time_s:frame.mediaTime}};
          frameCallback=media.requestVideoFrameCallback(track);
        };
        if(frameCallback!==null)media.cancelVideoFrameCallback?.(frameCallback);
        if(media.requestVideoFrameCallback)frameCallback=media.requestVideoFrameCallback(track);
      }
      played();
    };
    media.onwaiting=()=>{if(itemStarted&&firstPlayed!==null&&waitingSince===null){stalls++;waitingSince=performance.now();updateMetrics();}};
    media.onended=()=>{if(mine!==epoch)return;partEndedAt=performance.now();captionText='';updateCaptions();if(item.video)holdPicture();if(waitingSince!==null){waitingSeconds+=(performance.now()-waitingSince)/1000;waitingSince=null;}updateMetrics();};
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
      if(mine===epoch&&error.name!=="AbortError"){if(item.video)holdPicture();notice(error.message,true);$("resume").hidden=false;}
    }
    releaseSpeech();
    if(mine===epoch&&objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
  }
  if(mine===epoch){playing=false;captionText='';abortMedia=null;settleIdle();listenAfter=performance.now()+450;controls();}
}
$("resume").addEventListener("click",async()=>{
  if(lastMedia?.video&&$("video").hidden){const item={...lastMedia,stream:null};resetPlayback(true);queue.push(item);drain();return;}
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
      if(!pendingStop&&job.action){setAction(job.action);motionRequested=job.action!=='none';}
      if(job.text){replyNode??=bubble("","assistant");if(replyNode.textContent!==job.text){replyNode.textContent=job.text;$("chat").scrollTop=$("chat").scrollHeight;}}
      if(job.state==='done'&&job.message&&!shownMessage){bubble(job.message,'assistant sent-message');shownMessage=true;if(viewMode!=='text')unread++;controls();}
      if(job.portrait&&!shownPortrait&&replyNode){const image=document.createElement("img");image.src=job.portrait;image.alt="Mira in the "+sceneNames[job.scene].toLowerCase();replyNode.parentElement.append(image);shownPortrait=true;$("chat").scrollTop=$("chat").scrollHeight;}
      while(!pendingStop&&consumed<job.chunks.length){queue.push({...job.chunks[consumed++],jobId:key});drain();}
      if(!pendingStop){
        if(job.state==="thinking")notice("Mira is thinking…");
        else if(job.state==="transcribing")notice("Listening to your message…");
        else if(job.state==="rendering"&&!playing)notice("Connecting the picture…");
        else if(job.state==="speaking"&&!playing)notice("Preparing your reply…");
      }
      if(["done","failed","cancelled"].includes(job.state)){
        if(!pendingStop&&job.state==='done'&&job.presentation==='video'){nextIdleURL=job.idle_video||null;if(!playing&&!queue.length)settleIdle();}
        if(job.state==="failed"&&job.error_code==="no_speech"){node.parentElement.remove();notice("No speech detected. Please speak again.");}
        else if(job.state==="failed"){notice(job.error,true);if(!replyNode)bubble("That reply couldn't finish. Please try again.","assistant");}
        else if(job.state==="cancelled")notice(callInput.capturing()?'Listening…':replyMode==='text'?"Stopped. You can send another message.":"Stopped. You can speak now.");
        else if($("resume").hidden){notice(job.remembered?.length?"Saved what you shared. You can review it in Memory.":"");}
        lastServerSeconds=job.metrics.total_s??null;updateMetrics();
        break;
      }
      await sleep(100);
    }
  }catch(error){notice(error.message,true);}
  finally{if(active===key){active=null;busy=false;controls();}}
}
async function submit(text,raw=null,inputMode=null,draftId='message'){
  if(busy||stopping||!ready||(!raw&&!text.trim()))return;
  resetPlayback(true);lastStart=performance.now();firstPlayed=null;stalls=0;waitingSince=null;waitingSeconds=0;lastServerSeconds=null;updateMetrics();
  pendingStop=false;submitting=true;busy=true;controls();
  const node=bubble(raw?"Listening…":text,"user");
  if(!raw)$(draftId).value="";
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
  }catch(error){submitting=false;busy=false;if(!raw&&!$(draftId).value)$(draftId).value=text;controls();notice(error.message,true);}
}
$("composer").addEventListener("submit",e=>{e.preventDefault();submit($("message").value);});
$("message").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();submit($("message").value);}});
function callKeyboard(){
  const viewport=window.visualViewport;
  const offset=viewport&&document.activeElement===$('call-message')?Math.max(0,innerHeight-viewport.height-viewport.offsetTop):0;
  document.querySelector('.conversation').style.setProperty('--keyboard-offset',offset+'px');
}
window.visualViewport?.addEventListener('resize',callKeyboard);
window.visualViewport?.addEventListener('scroll',callKeyboard);
for(const event of ['focus','blur'])$('call-message').addEventListener(event,callKeyboard);
$('call-type').addEventListener('click',()=>{
  callInputOpen=!callInputOpen;controls();
  if(callInputOpen)$('call-message').focus();else $('call-message').blur();
});
function sendCallText(){
  const text=$('call-message').value.trim();
  if(!text||$('call-send').disabled)return;
  callInput.turn({text,mode:replyMode,draftId:'call-message'},{interrupt:busy||playing});
  controls();
}
$('call-message').addEventListener('input',controls);
$('call-composer').addEventListener('submit',e=>{e.preventDefault();sendCallText();});
$('call-message').addEventListener('keydown',e=>{
  if(e.key==='Escape'){callInputOpen=false;controls();$('call-type').focus();}
  else if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendCallText();}
});
async function interrupt(){
  if(stopping)return;
  pendingStop=true;
  const position=displayedPlayback?.id?structuredClone(displayedPlayback):null;
  // Older browsers report the current playback clock instead of presented frames.
  if(position&&!$('video').requestVideoFrameCallback&&!$('video').hidden)position.playback.time_s=$('video').currentTime;
  const key=position?.id||active;
  if(position)idleSuppressed=true;
  if(active||submitting)lastMedia=null;
  resetPlayback(true);
  const mine=epoch;
  if(submitting){pendingStop=true;return;}
  if(key){
    stopping=true;controls();
    try{
      const result=await api('/api/cancel',position||{id:key});
      if(mine!==epoch)return;
      if(result.pose_preserved){idleURL=result.idle_video||null;idleSuppressed=!idleURL;}
      notice(result.warning||(callInput.capturing()?'Listening…':'Reply stopped. You can speak now.'),Boolean(result.warning));
    }catch(error){if(mine===epoch)notice(error.message,true);return false;}
    finally{stopping=false;listenAfter=performance.now()+450;controls();}
  }
  else notice(replyMode==='text'?"Reply stopped. Send another message when you're ready.":"Reply stopped. You can speak now.");
}
$("stop").addEventListener("click",interrupt);
$('mic').addEventListener('click',async()=>{
  if(microphone.enabled||microphone.pending){microphone.stop();return;}
  try{await microphone.start();}catch(error){notice(error.message,true);}controls();
});
async function startCall(mode){
  if(!ready)return;
  const request=++callRequest,changed=replyMode!==mode;
  if(changed){microphone.stop();callInputOpen=false;}
  replyMode=mode;viewMode=mode;controls();
  if(changed){await interrupt();if(request!==callRequest)return;}
  notice();
  try{await microphone.start();}catch(error){notice(error.message,true);}controls();
}
for(const mode of ['text','voice','video'])$('mode-'+mode).addEventListener('click',async()=>{
  if(mode!=='text'&&replyMode!==mode&&ready){await startCall(mode);return;}
  viewMode=mode;if(mode==='text')unread=0;controls();notice();
  if(mode==='text')$('chat').scrollTop=$('chat').scrollHeight;
});
$('join-call').addEventListener('click',()=>startCall(viewMode==='voice'?'voice':'video'));
$('end-call').addEventListener('click',async()=>{callRequest++;microphone.stop();replyMode='text';viewMode='text';await interrupt();controls();notice('Call ended. Your messages are here.');});
$('return-call').addEventListener('click',()=>{if(replyMode!=='text'){viewMode=replyMode;controls();notice();}});
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
  try{callRequest++;microphone.stop();replyMode=viewMode="text";unread=0;resetPlayback();await api("/api/reset",{});active=null;busy=false;lastMedia=null;$("replay").hidden=true;$("chat").replaceChildren();$("memory").value="";renderFacts();$("settings").close();setScene("mira");notice("Conversation and memory cleared.");controls();}catch(error){notice(error.message,true);}
});
window.addEventListener("pagehide",()=>{callRequest++;microphone.stop();abortMedia?.abort();});
async function boot(){
  for(;;){
    try{
      if(!connected){
        const data=await api("/api/bootstrap");
        const restarted=token&&token!==data.token;token=data.token;connected=true;
        if(firstBoot||restarted){renderHistory(data.turns);setScene(data.scene||"mira");firstBoot=false;}
        if(restarted){idleSuppressed=false;idleFailed=false;resetPlayback();active=null;busy=false;notice("Reconnected. Send your message again if the last reply was interrupted.");}
      }
      const state=await api("/api/status");ready=state.ready;hasVideo=state.visual_loaded;provider=state.provider;
      if(!active&&!playing&&!submitting&&!state.busy)idleURL=state.idle_video||null;
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
