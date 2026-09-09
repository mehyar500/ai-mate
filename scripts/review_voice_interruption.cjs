// Actual microphone module, AudioWorklet, VAD, local ASR and GPU renderer.
// getUserMedia is replaced by generated PCM, with a simulated AEC-enabled
// setting. This tests application flow, not acoustic echo cancellation.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const folder=path.resolve(__dirname,'../generated/local-app/audit/speech-interruption-voice-primed');
async function main(){
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:716,height:854}});
    const errors=[],posts=[],stops=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(new URL(r.url()).pathname==='/api/audio')posts.push(Date.now());});
    await page.addInitScript(()=>{
      navigator.mediaDevices.getUserMedia=async constraints=>{
        if(constraints.video!==false)throw Error('This test never provides camera access.');
        const context=new AudioContext();await context.resume();
        const target=context.createMediaStreamDestination();
        const track=target.stream.getAudioTracks()[0],original=track.getSettings.bind(track);
        track.getSettings=()=>({...original(),echoCancellation:true});
        window.feedSpeech=async encoded=>{
          await context.resume();
          const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
          const audio=await context.decodeAudioData(bytes.buffer);
          const source=context.createBufferSource();source.buffer=audio;source.connect(target);
          const started=Date.now();source.start();return {started,duration:audio.duration};
        };
        return target.stream;
      };
    });
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    await page.locator('#join-call').click();
    await page.waitForFunction(()=>typeof window.feedSpeech==='function');
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    const getJob=async key=>(await page.request.get('http://127.0.0.1:8766/api/jobs/'+key,{headers:{'X-Local-Token':token}})).json();
    async function feed(name){return page.evaluate(encoded=>window.feedSpeech(encoded),fs.readFileSync(path.join(folder,name+'.wav')).toString('base64'));}
    async function response(){const r=await page.waitForResponse(r=>new URL(r.url()).pathname==='/api/audio',{timeout:30000});assert.equal(r.status(),202);return (await r.json()).id;}
    async function complete(key){
      let job;const deadline=Date.now()+45000;
      do{job=await getJob(key);if(['done','cancelled','failed'].includes(job.state))break;await page.waitForTimeout(100);}while(Date.now()<deadline);
      assert.equal(job.state,'done',job.error);
      await page.waitForFunction(()=>document.querySelector('#video').hidden&&document.querySelector('#stop').hidden,{}, {timeout:45000});
      await page.waitForTimeout(550);
      return job;
    }
    const firstResponse=response();await feed('approach');const first=await firstResponse;
    await page.waitForFunction(()=>{const v=document.querySelector('#video');return !v.hidden&&!v.paused&&v.currentTime>=.6;}, {}, {timeout:45000});
    const stopResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/cancel');
    const nextResponse=response();
    const onset=await feed('interrupt');
    const stoppedResponse=await stopResponse;
    const stopped=await stoppedResponse.json(),request=stoppedResponse.request().postDataJSON();
    stops.push({request,stopped,onset,received:Date.now()});
    assert.equal(stoppedResponse.status(),200);assert.equal(request.id,first);assert.equal(stopped.pose_preserved,true);
    assert.ok(request.playback.time_s>=.6&&request.playback.time_s<1.8);
    const held=await page.locator('#held-frame').evaluate(el=>el.toDataURL('image/png'));
    fs.writeFileSync(path.join(folder,'browser-held.png'),Buffer.from(held.split(',')[1],'base64'));
    await page.screenshot({path:path.join(folder,'voice-stopped.png')});
    const second=await nextResponse;
    const next=await complete(second);
    assert.match(next.user,/^actually/i);assert.match(next.user,/name of my dog/i);
    assert.equal(next.chunks[0].render.continues_previous_pose,true);assert.equal(next.prepared_pose,null);
    const backResponse=response();await feed('return');const back=await complete(await backResponse);
    assert.equal(back.prepared_pose,'base');
    assert.equal(back.chunks[0].render.motion_source,'reviewed_prepared_transition');
    assert.deepEqual(errors,[]);assert.equal(posts.length,3);
    const finalFirst=await getJob(first);assert.equal(finalFirst.state,'cancelled');
    await page.locator('#end-call').click();
    await page.waitForTimeout(800);assert.equal(posts.length,3);
    const result={stops,posts,first_state:finalFirst.state,next,back,pageErrors:errors,
      scope:'Synthetic PCM through real browser microphone/VAD and local ASR. Simulated echoCancellation setting; deterministic planner. Actual GPU media, playback and pose-preserving voice cancellation. No physical microphone or acoustic echo test.'};
    fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({stops,posts:posts.length,next_user:next.user,back_pose:back.prepared_pose,pageErrors:errors}));
  }finally{
    await browser.close();
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true}));
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
