"use strict";
const $ = id => document.getElementById(id);
let token = "", mode = "voice", ready = false, busy = false, active = null, generation = 0;
let audioContext, stream, recorder, recording = false, micPending = false, samples = [], recordTimer, recordStart;
let playQueue = [], playing = false, lastMedia = null;
let submitting = false, pendingStop = false, hasPortrait = false, visualError = null;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function notice(text = "", error = false) { $("notice").textContent = text; $("notice").className = error ? "error" : ""; }
async function api(path, body, extra = {}) {
  const response = await fetch(path, {method: body === undefined ? "GET" : "POST", headers: {"X-Local-Token": token, ...(body === undefined ? {} : {"Content-Type": "application/json"}), ...extra.headers}, body: body === undefined ? undefined : JSON.stringify(body)});
  const data = await response.json(); if (!response.ok) throw new Error(data.error || "Local request failed."); return data;
}
function controls() {
  $("send").disabled = !ready || busy || recording || micPending;
  $("record").disabled = !ready || busy || micPending;
  $("stop").hidden = !busy && !playing && !recording;
  $("stop").textContent = recording ? "Discard recording" : "Stop reply";
  document.querySelectorAll("[data-mode]").forEach(b => {b.disabled = busy || recording || micPending || (b.dataset.mode === "video" && (!hasPortrait || visualError));});
  $("scene").disabled = busy || recording || micPending;
  $("reset").disabled = micPending || recording || submitting;
}
function bubble(text, role) {
  const empty = $("chat").querySelector(".empty"); if (empty) empty.remove();
  const div = document.createElement("div"); div.className = "bubble " + role;
  const label = document.createElement("span"); label.className = "speaker"; label.textContent = role === "user" ? "YOU" : "MIRA";
  const content = document.createElement("span"); content.textContent = text; div.append(label, content); $("chat").append(div); $("chat").scrollTop = $("chat").scrollHeight; return content;
}
function history(turns) { $("chat").replaceChildren(); turns.forEach(t => {bubble(t.user, "user"); bubble(t.assistant, "assistant");}); }
function stopPlayback() {
  generation++; playQueue = []; playing = false;
  for (const el of [$("audio"), $("video")]) {el.pause(); el.removeAttribute("src"); el.load();}
  $("video").hidden = true; $("media-label").textContent = "Prepared AI portrait";
  controls();
}
async function drain() {
  if (playing) return; playing = true; controls(); const epoch = generation;
  while (playQueue.length && epoch === generation) {
    const item = playQueue.shift(); lastMedia = item; $("replay").hidden = false;
    const media = item.video ? $("video") : $("audio");
    media.src = item.video || item.audio;
    if (item.video) {media.hidden = false; $("media-label").textContent = "Generated lip-sync reply";}
    try {
      await media.play();
      await Promise.race([new Promise(resolve => {media.onended = resolve; media.onerror = resolve; media.onemptied = resolve;}), sleep((item.duration_s + 4) * 1000)]);
    } catch {notice("Reply is ready. Select Play latest reply to hear it.");}
    if (item.video && epoch === generation) {media.hidden = true; $("media-label").textContent = "Prepared AI portrait";}
  }
  if (epoch === generation) {playing = false; controls();}
}
async function follow(key, userNode) {
  active = key; let assistantNode = null, consumed = 0;
  const states = {thinking: "Thinking…", speaking: "Preparing speech…", rendering: "Preparing your video reply…", warming_video: "Loading the portrait model — first video takes longer.", transcribing: "Listening to your recording…"};
  try {
    for (;;) {
      const job = await api("/api/jobs/" + key);
      if (active !== key) return;
      if (job.user) userNode.textContent = job.user;
      if (job.text) {if (!assistantNode) assistantNode = bubble("", "assistant"); assistantNode.textContent = job.text;}
      while (consumed < job.chunks.length) {playQueue.push(job.chunks[consumed++]); drain();}
      notice(states[job.state] || "");
      if (["done", "failed", "cancelled"].includes(job.state)) {
        if (job.state === "failed") notice(job.error, true);
        if (job.state === "cancelled") notice("Reply stopped. You can send a new message.");
        if (job.metrics.first_media_ready_s) $("metrics").textContent = `First media ready ${job.metrics.first_media_ready_s.toFixed(2)}s · server timing`;
        break;
      }
      await sleep(200);
    }
  } catch (error) {notice(error.message, true);}
  finally {if (active === key) {active = null; busy = false; controls();}}
}
async function send(text) {
  if (!text.trim() || busy || !ready || recording || micPending) return;
  stopPlayback(); pendingStop = false; submitting = true; busy = true; controls(); notice("Thinking…"); const userNode = bubble(text, "user"); $("message").value = "";
  try {const {id} = await api("/api/turn", {text, mode, scene: $("scene").value}); submitting = false; active = id; if (pendingStop) await api("/api/cancel", {id}); await follow(id, userNode);}
  catch(error) {submitting = false; busy = false; controls(); notice(error.message, true); $("message").value = text;}
}
$("composer").addEventListener("submit", e => {e.preventDefault(); send($("message").value);});
$("message").addEventListener("keydown", e => {if (e.key === "Enter" && !e.shiftKey) {e.preventDefault(); send($("message").value);}});
document.querySelectorAll("[data-prompt]").forEach(b => b.addEventListener("click", () => send(b.dataset.prompt)));
document.querySelectorAll("[data-mode]").forEach(b => b.addEventListener("click", () => {
  mode = b.dataset.mode; document.querySelectorAll("[data-mode]").forEach(el => el.setAttribute("aria-pressed", String(el === b)));
  $("mode-note").textContent = {text:"Text only. No speech or video generation.", voice:"Spoken replies, generated on this computer.", video:"Short generated lip-sync replies. Allow extra preparation time."}[mode];
}));
$("scene").addEventListener("change", () => {stopPlayback(); $("portrait").src = "/portrait/" + $("scene").value + ".png";});
$("stop").addEventListener("click", async () => {
  if(recording) {recording=false;clearInterval(recordTimer);recorder.disconnect();stream.getTracks().forEach(t=>t.stop());await audioContext.close();samples=[];$("record").textContent="Record message";$("record-time").textContent="";controls();notice("Recording discarded.");return;}
  stopPlayback(); if (submitting) {pendingStop = true; notice("Stopping the pending reply…"); return;} if (active) {try {await api("/api/cancel", {id: active}); notice("Stopping the current reply…");} catch(e) {notice(e.message, true);}} else notice("Playback stopped.");
});
$("replay").addEventListener("click", () => {if (lastMedia) {stopPlayback(); playQueue.push(lastMedia); drain();}});
$("memory-toggle").addEventListener("click", () => {$("memory-panel").hidden = !$("memory-panel").hidden; $("memory-toggle").setAttribute("aria-expanded", String(!$("memory-panel").hidden));});
$("save-memory").addEventListener("click", async () => {try {await api("/api/memory", {memory:$("memory").value}); notice("Memory saved on this computer.");} catch(e) {notice(e.message, true);}});
$("reset").addEventListener("click", async () => {
  if (!confirm("Clear this local conversation and saved memory? Prepared portraits will remain.")) return;
  try {stopPlayback(); await api("/api/reset", {}); active = null; $("chat").replaceChildren(); $("memory").value = ""; lastMedia = null; $("replay").hidden = true; notice("Conversation and memory cleared.");}
  catch(e) {notice(e.message, true);}
});
function wavBlob(chunks, rate) {
  const size = chunks.reduce((n, a) => n + a.length, 0); const buffer = new ArrayBuffer(44 + size*2), v = new DataView(buffer);
  function str(offset, text) {for (let i=0;i<text.length;i++) v.setUint8(offset+i,text.charCodeAt(i));}
  str(0,"RIFF"); v.setUint32(4,36+size*2,true); str(8,"WAVE"); str(12,"fmt "); v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true); v.setUint32(24,rate,true); v.setUint32(28,rate*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true); str(36,"data"); v.setUint32(40,size*2,true);
  let offset=44; for (const chunk of chunks) for (const value of chunk) {v.setInt16(offset,Math.max(-1,Math.min(1,value))*32767,true); offset+=2;}
  return new Blob([buffer],{type:"audio/wav"});
}
async function finishRecording() {
  if (!recording) return; recording=false; pendingStop=false; submitting=true; busy=true; controls(); clearInterval(recordTimer); recorder.disconnect(); stream.getTracks().forEach(t => t.stop());
  const rate=audioContext.sampleRate; await audioContext.close(); $("record").textContent="Record message"; $("record-time").textContent="";
  const raw=wavBlob(samples,rate); samples=[]; busy=true; controls(); stopPlayback(); const userNode=bubble("Transcribing your recording…","user"); notice("Transcribing locally…");
  try {const response=await fetch("/api/audio",{method:"POST",headers:{"Content-Type":"audio/wav","X-Local-Token":token,"X-Reply-Mode":mode,"X-Scene":$("scene").value},body:raw}); const data=await response.json(); if(!response.ok) throw new Error(data.error); submitting=false; active=data.id; if(pendingStop) await api("/api/cancel",{id:data.id}); await follow(data.id,userNode);}
  catch(e) {submitting=false; busy=false; controls(); notice(e.message,true);}
}
$("record").addEventListener("click",async () => {
  if (recording) return finishRecording();
  if(micPending || busy) return;
  stopPlayback();micPending=true;controls();
  try {
    stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
    audioContext=new AudioContext(); await audioContext.resume(); await audioContext.audioWorklet.addModule("/recorder.js");
    recorder=new AudioWorkletNode(audioContext,"local-recorder"); samples=[];
    recorder.port.onmessage=e => {if(recording) samples.push(new Float32Array(e.data));};
    const source=audioContext.createMediaStreamSource(stream); source.connect(recorder); recorder.connect(audioContext.destination);
    recording=true;micPending=false; recordStart=Date.now(); $("record").textContent="Send recording"; controls(); notice("Recording locally. Click Send recording when finished.");
    recordTimer=setInterval(() => {const elapsed=(Date.now()-recordStart)/1000; $("record-time").textContent=elapsed.toFixed(0)+" / 30s"; if(elapsed>=29) finishRecording();},250);
  } catch(e) {if(stream)stream.getTracks().forEach(t=>t.stop()); if(audioContext && audioContext.state!=="closed") await audioContext.close(); recording=false;micPending=false; controls(); notice("Microphone unavailable or permission denied. You can still type.",true);}
});
window.addEventListener("pagehide",()=>{if(stream)stream.getTracks().forEach(t=>t.stop());});
async function boot() {
  try {
    const data=await api("/api/bootstrap"); token=data.token; $("memory").value=data.memory; if(data.turns.length) history(data.turns);
    const scenes=data.scenes; hasPortrait=!!scenes.length; if (scenes.length) {$("scene").replaceChildren(); for(const s of scenes) {const o=document.createElement("option");o.value=s;o.textContent={mira:"Living room",garden:"Garden",cafe:"Café"}[s];$("scene").append(o);}}
    if(!scenes.length) {$("portrait").hidden=true;notice("Prepare a local portrait to enable video replies.");}
    for(;;) {const state=await api("/api/status"); ready=state.ready; busy=state.busy || active !== null || submitting; if(state.visual_error && !visualError)notice(state.visual_error,true); visualError=state.visual_error; $("connection").textContent=state.error ? "Model startup failed" : ready ? "On your computer" : "Loading local models"; $("dot").classList.toggle("ready",ready); if(state.error)notice(state.error,true); controls(); await sleep(1500);}
  } catch(e) {ready=false;controls();$("connection").textContent="Local server disconnected";notice("Connection lost. Restart the local server and reload this page.",true);}
}
boot();
