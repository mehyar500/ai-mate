// Neutral isolated engine on 8766: actual ASR/planning/TTS/GPU/media.
// --capture uses real turn detection with a synthetic input MediaStream.
// Default WAV injection bypasses capture and endpoint detection.
const {chromium}=require('playwright');
const {installFrameProbe}=require('./playback_probe.cjs');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const trial=process.argv[2];assert.ok(['qualification','soak'].includes(trial));
const label=process.argv[3]||'';assert.ok(!label||/^[a-z0-9-]{1,32}$/.test(label));
const capture=process.argv[4]==='--capture';assert.ok(!process.argv[4]||capture);
assert.ok(!process.argv[5]||process.argv[5]==='--startup-buffer-ms');
assert.equal(Boolean(process.argv[5]),Boolean(process.argv[6]));
const appCode=fs.readFileSync(path.resolve(__dirname,'../local_app/web/app.js'),'utf8');
const probeCode=fs.readFileSync(path.join(__dirname,'playback_probe.cjs'),'utf8');
const bufferCondition=appCode.match(/media\.buffered\.end\(0\)>=([.\d]+)/g);assert.equal(bufferCondition?.length,1);
const currentBufferMs=Math.round(Number(bufferCondition[0].split('>=')[1])*1000);
const startupBufferMs=process.argv[6]?Number(process.argv[6]):currentBufferMs;assert.ok([150,350].includes(startupBufferMs));
assert.ok(!process.argv[7]);
const folder=path.resolve(__dirname,'../generated/local-app/audit/voice-video-'+trial+(label?'-'+label:''));
const totalMs=trial==='soak'?30*60*1000:0;
async function main(){
  // Preserve synthetic test outputs before the app's normal 50-turn pruning.
  // This does not change retention in the live application or copy its memory.
  const retained=path.join(folder,'retained-media');fs.mkdirSync(retained,{recursive:true});
  const browser=await chromium.launch({headless:true});
  const results=[],errors=[];
  let stoppedEarly=false;
  let started=Date.now();
  try{
    const page=await browser.newPage({viewport:{width:716,height:854}});
    page.on('pageerror',e=>errors.push(e.message));
    if(startupBufferMs!==currentBufferMs){
      await page.route('**/app.js',route=>route.fulfill({contentType:'text/javascript',body:appCode.replace(bufferCondition[0],'media.buffered.end(0)>='+startupBufferMs/1000)}));
    }
    if(capture)await page.addInitScript(()=>{
      let context,destination;
      Object.defineProperty(navigator.mediaDevices,'getUserMedia',{configurable:true,value:async()=>{
        context??=new AudioContext();await context.resume();
        destination=context.createMediaStreamDestination();
        return destination.stream;
      }});
      window.benchmarkEmit=async encoded=>{
        const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
        const buffer=await context.decodeAudioData(bytes.buffer),samples=buffer.getChannelData(0);
        let lastVoice=0;
        for(let i=0;i<samples.length;i+=128){
          const end=Math.min(samples.length,i+128);let sum=0;
          for(let j=i;j<end;j++)sum+=samples[j]*samples[j];
          if(Math.sqrt(sum/(end-i))>.009)lastVoice=end;
        }
        if(!lastVoice)throw Error('Synthetic fixture has no speech energy');
        const source=context.createBufferSource();source.buffer=buffer;source.connect(destination);
        const startAt=context.currentTime+.05;
        window.benchmarkVoiceEnd=performance.now()+(startAt-context.currentTime+lastVoice/buffer.sampleRate)*1000;
        await new Promise(resolve=>{source.onended=()=>{source.disconnect();resolve();};source.start(startAt);});
      };
    });
    else await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
      export class Microphone {
        constructor(o){this.options=o;this.enabled=false;}
        async start(){this.enabled=true;this.options.onState('listening');
          window.benchmarkEmit=encoded=>{if(!this.enabled)throw Error('Call stopped');
            this.options.onTurn(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)));};}
        stop(){this.enabled=false;this.options.onState('off');}
      }`}));
    // Cold model initialization can outlast process creation. Wait for actual
    // readiness so an early driver cannot terminate a warming benchmark.
    const readyDeadline=Date.now()+90000;
    let ready=false;
    while(Date.now()<readyDeadline){
      let bootstrap;
      try{
        const response=await page.request.get('http://127.0.0.1:8766/api/bootstrap',{timeout:1000});
        if(response.ok())bootstrap=await response.json();
      }catch{}
      if(bootstrap?.error)throw Error('Benchmark model startup failed. Inspect the local server log.');
      if(bootstrap?.ready){ready=true;break;}
      await page.waitForTimeout(500);
    }
    assert.ok(ready,'Benchmark did not become ready within 90 seconds');
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    await page.locator('#join-call').click();
    if(capture)await page.waitForTimeout(600);
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    const getJob=async id=>(await page.request.get('http://127.0.0.1:8766/api/jobs/'+id,{headers:{'X-Local-Token':token}})).json();
    await page.evaluate(()=>{
      window.qual={events:[],appends:[],start:performance.now(),frames:{},avClockSkewMs:[]};
      for(const Source of new Set([window.MediaSource,window.ManagedMediaSource].filter(Boolean))){
        const original=Source.prototype.addSourceBuffer;
        Source.prototype.addSourceBuffer=function(mime){
          const buffer=original.call(this,mime);
          buffer.addEventListener('updateend',()=>window.qual.appends.push({at:(performance.now()-window.qual.start)/1000,
            bufferedEnd:buffer.buffered.length?buffer.buffered.end(buffer.buffered.length-1):null}));
          return buffer;
        };
      }
      for(const id of ['video','audio'])for(const type of ['playing','ended','waiting','error']){
        const el=document.getElementById(id);
        el.addEventListener(type,()=>window.qual.events.push({id,type,at:(performance.now()-window.qual.start)/1000,
          time:el.currentTime,muted:el.muted,volume:el.volume}));
      }
    });
    await page.evaluate(installFrameProbe);
    started=Date.now();
    const cases=JSON.parse(fs.readFileSync(path.join(folder,'fixtures.json')));
    const fixtures=trial==='soak'?Array.from({length:6},()=>cases).flat():cases;
    for(const [index,fixture] of fixtures.entries()){
      const wait=started+index*totalMs/fixtures.length-Date.now();
      if(wait>0)await page.waitForTimeout(wait);
      const row={case:fixture.case,cycle:Math.floor(index/cases.length)+1,expected:fixture,input:index%2?'text':'audio',failures:[]};
      try{
        await page.evaluate(()=>{window.qual.events=[];window.qual.appends=[];window.qual.start=performance.now();});
        const endpoint=index%2?'/api/turn':'/api/audio';
        const submitted=page.waitForResponse(r=>new URL(r.url()).pathname===endpoint);
        if(index%2){
          if(await page.locator('#call-composer').isHidden())await page.locator('#call-type').click();
          await page.locator('#call-message').fill(fixture.prompt);
          await page.locator('#call-send').click();
        }else{
          await page.evaluate(encoded=>window.benchmarkEmit(encoded),fs.readFileSync(path.join(folder,fixture.case+'.wav')).toString('base64'));
        }
        const response=await submitted;assert.equal(response.status(),202);
        row.id=(await response.json()).id;
        if(fixture.interrupt_s){
          await page.waitForFunction(t=>{const v=document.querySelector('#video');return !v.hidden&&!v.paused&&v.currentTime>=t;},fixture.interrupt_s,{timeout:60000});
          const cancelled=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/cancel');
          await page.locator('#stop').click();
          row.cancel=await (await cancelled).json();assert.equal(row.cancel.pose_preserved,true);
          await page.waitForFunction(()=>document.querySelector('#video').hidden&&!document.querySelector('#held-frame').hidden);
        }
        let job;const deadline=Date.now()+60000;
        do{job=await getJob(row.id);if(['done','failed','cancelled'].includes(job.state))break;await page.waitForTimeout(100);}while(Date.now()<deadline);
        row.job=job;
        if(fixture.interrupt_s)assert.ok(['done','cancelled'].includes(job.state),job.error);
        else assert.equal(job.state,'done',job.error);
        if(!fixture.interrupt_s){
          await page.waitForFunction(n=>['video','audio'].every(id=>window.qual.events.filter(e=>e.id===id&&e.type==='ended').length>=n),job.chunks.length,{timeout:60000});
        }
        Object.assign(row,await page.evaluate(()=>({events:window.qual.events,appends:window.qual.appends,metrics:document.querySelector('#metrics').textContent,
          audio:{muted:document.querySelector('#audio').muted,ended:document.querySelector('#audio').ended}})));
        if(capture&&row.input==='audio'){
          row.speech_end_to_playback_s=await page.evaluate(()=>{
            const starts=['audio','video'].map(id=>window.qual.events.find(e=>e.id===id&&e.type==='playing')?.at);
            return starts.every(Number.isFinite)?(window.qual.start+Math.max(...starts)*1000-window.benchmarkVoiceEnd)/1000:null;
          });
        }
        if(job.action!==fixture.action)row.failures.push('wrong_action');
        if('pose' in fixture&&job.prepared_pose!==fixture.pose)row.failures.push('wrong_pose');
        if(fixture.reply_contains&&!job.text.toLowerCase().includes(fixture.reply_contains.toLowerCase()))row.failures.push('memory_recall');
        if(fixture.unsupported&&!/cannot|can't|not able|unavailable|not supported/i.test(job.text))row.failures.push('unsupported_action_claim');
        if(!fixture.interrupt_s&&!/Buffer waits: 0/.test(row.metrics))row.failures.push('playback_stall');
        if(!row.events.some(e=>e.id==='audio'&&e.type==='playing'&&!e.muted&&e.volume>0))row.failures.push('audio_playback');
        if(fixture.message_contains){
          await page.locator('#mode-text').click();
          if(!(await page.locator('#chat').innerText()).toLowerCase().includes(fixture.message_contains))row.failures.push('message_delivery');
          if(await page.locator('#active-call').isHidden())row.failures.push('call_dropped_on_navigation');
          await page.locator('#return-call').click();
          if(await page.locator('#end-call').isHidden())row.failures.push('call_not_resumed');
        }
      }catch(error){
        row.failures.push(error.message);
        Object.assign(row,await page.evaluate(()=>({events:window.qual.events,appends:window.qual.appends,
          metrics:document.querySelector('#metrics').textContent,notice:document.querySelector('#notice').textContent,
          audio:{muted:document.querySelector('#audio').muted,ended:document.querySelector('#audio').ended},
          video:{ended:document.querySelector('#video').ended,readyState:document.querySelector('#video').readyState}})));
      }
      row.retainedMedia=[];
      for(const chunk of row.job?.chunks||[]){
        const name=chunk.audio?.split('/').at(-1);
        if(!name||!/^[a-f0-9]{32}-\d+\.wav$/.test(name))throw Error('Invalid benchmark media name');
        for(const mediaName of [name,name.replace(/\.wav$/,'.mp4')]){
          const source=path.join(folder,mediaName);
          if(fs.existsSync(source)){fs.copyFileSync(source,path.join(retained,mediaName));row.retainedMedia.push(mediaName);}
        }
      }
      results.push(row);
      fs.writeFileSync(path.join(folder,'qualification.json'),JSON.stringify({elapsed_s:(Date.now()-started)/1000,results,errors},null,2)+'\n');
      console.log(JSON.stringify({case:row.case,cycle:row.cycle,input:row.input,metrics:row.metrics,failures:row.failures}));
      // A soak with three failed turns is already disqualified. Preserve its
      // playback statistics and close normally instead of spending the balance
      // of thirty minutes on a known failing candidate.
      if(trial==='soak'&&results.filter(r=>r.failures.length).length>=3){stoppedEarly=true;break;}
      await page.waitForTimeout(500);
    }
    const remaining=started+totalMs-Date.now();if(!stoppedEarly&&remaining>0)await page.waitForTimeout(remaining);
    const playback=await page.evaluate(()=>{
      const samples=window.qual.avClockSkewMs.sort((a,b)=>a-b);
      return {frames:window.qual.frames,callActive:!document.querySelector('#end-call').hidden,
        av_clock_skew_ms:{samples:samples.length,p50:samples[Math.ceil(samples.length*.5)-1],
          p95:samples[Math.ceil(samples.length*.95)-1],max:samples.at(-1)},
        av_scope:'Presented video timestamps versus playing audio clock; not acoustic output or perceptual phoneme alignment.'};
    });
    await page.locator('#end-call').click();
    const latency=results.filter(r=>!r.expected.interrupt_s).map(r=>Number(r.metrics?.match(/First playback: ([\d.]+)s/)?.[1])).filter(Number.isFinite).sort((a,b)=>a-b);
    const speechLatency=results.filter(r=>!r.expected.interrupt_s&&Number.isFinite(r.speech_end_to_playback_s)).map(r=>r.speech_end_to_playback_s).sort((a,b)=>a-b);
    const summary={elapsed_s:(Date.now()-started)/1000,turns:results.length,startup_buffer_ms:startupBufferMs,
      stopped_early_for_failures:stoppedEarly,soak_duration_met:trial==='soak'?Date.now()-started>=totalMs:null,
      runtime_app_sha256:crypto.createHash('sha256').update(appCode).digest('hex'),buffer_override:startupBufferMs!==currentBufferMs,
      frame_probe_sha256:crypto.createHash('sha256').update(probeCode).digest('hex'),
      failures:results.filter(r=>r.failures.length).map(r=>({case:r.case,cycle:r.cycle,failures:r.failures})),
      response_sample_count:latency.length,p50_s:latency[Math.ceil(latency.length*.5)-1],p95_s:latency[Math.ceil(latency.length*.95)-1],playback,errors,
      speech_end_to_playback_s:{samples:speechLatency.length,p50:speechLatency[Math.ceil(speechLatency.length*.5)-1],p95:speechLatency[Math.ceil(speechLatency.length*.95)-1]},
      scope:capture?'Synthetic speech enters a virtual MediaStream through real AudioWorklet/turn detection/ASR/planning/TTS/GPU/browser playback. End-of-speech uses last synthetic block above the VAD energy floor. Physical acoustics and network/mobile devices excluded.':'Mixed synthetic WAV and typed commands; actual ASR/Cloudflare/Kokoro/MuseTalk/browser playback. Physical capture, endpoint detection and network/device testing excluded. Frame callbacks do not prove anatomy, identity or perceptual lip sync.'};
    fs.writeFileSync(path.join(folder,'summary.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
    if(summary.failures.length||summary.errors.length)process.exitCode=1;
  }finally{await browser.close();fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true,turns:results.length}));}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
