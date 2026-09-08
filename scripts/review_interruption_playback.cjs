// Actual GPU video, MSE, audio and cancellation on isolated port 8766.
// The microphone is replaced; no private history or captured speech is used.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const middle=process.argv[2]==='middle';
const stopAt=middle?1.6:.8;
const folder=path.resolve(__dirname,'../generated/local-app/audit/speech-interruption'+(middle?'-middle':''));
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main(){
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:716,height:854}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
      export class Microphone {
        constructor(options){this.options=options;this.enabled=false;window.syntheticMic=this;}
        async start(){this.enabled=true;this.options.onState('listening');}
        stop(){this.enabled=false;this.options.onState('off');}
      }`}));
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    await page.locator('#join-call').click();
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    async function getJob(key){
      return (await page.request.get('http://127.0.0.1:8766/api/jobs/'+key,{headers:{'X-Local-Token':token}})).json();
    }
    async function send(value){
      await page.waitForFunction(()=>window.syntheticMic.options.canListen(),{}, {timeout:45000});
      const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/audio');
      await page.evaluate(value=>{window.syntheticMic.options.onTurn(new Uint8Array([value]));},value);
      return (await (await response).json()).id;
    }
    async function finished(key){
      const deadline=Date.now()+45000;let job;
      do{job=await getJob(key);if(['done','failed','cancelled'].includes(job.state))break;await delay(100);}while(Date.now()<deadline);
      assert.equal(job.state,'done',job.error);
      await page.waitForFunction(()=>window.syntheticMic.options.canListen(),{}, {timeout:45000});
      return job;
    }
    const approach=await send(1);
    const waitStarted=Date.now();
    await page.waitForFunction(stopAt=>{
      const v=document.querySelector('#video');return !v.hidden&&!v.paused&&v.currentTime>=stopAt;
    },stopAt, {timeout:45000});
    const readyToStop=await page.locator('#video').evaluate(v=>({time:v.currentTime,hidden:v.hidden,now:Date.now()}));
    const stoppedResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/cancel');
    await page.locator('#stop').click();
    const response=await stoppedResponse;
    const request=response.request().postDataJSON();
    const stopped=await response.json();
    fs.writeFileSync(path.join(folder,'stop-request.json'),JSON.stringify({waitStarted,readyToStop,request,stopped,received:Date.now()},null,2)+'\n');
    assert.equal(response.status(),200);
    assert.equal(request.id,approach);
    assert.equal(request.playback.index,0);
    assert.ok(request.playback.time_s>=stopAt-.1&&request.playback.time_s<stopAt+.5);
    assert.equal(stopped.pose_preserved,true,stopped.warning);
    assert.equal(stopped.idle_video,null);
    await page.waitForFunction(()=>!document.querySelector('#held-frame').hidden);
    const held=await page.locator('#held-frame').evaluate(el=>el.toDataURL('image/png'));
    fs.writeFileSync(path.join(folder,'browser-held.png'),Buffer.from(held.split(',')[1],'base64'));
    await page.screenshot({path:path.join(folder,'stopped-screen.png')});
    await delay(500); // Let the benchmark save the protected frame before the next turn.
    const ordinary=await send(2);
    await page.waitForFunction(()=>{
      const v=document.querySelector('#video');return !v.hidden&&!v.paused&&v.currentTime>=.25;
    },{}, {timeout:45000});
    await page.screenshot({path:path.join(folder,'reply-from-stopped-pose.png')});
    const ordinaryJob=await finished(ordinary);
    const ordinaryMetrics=await page.locator('#metrics').textContent();
    assert.equal(ordinaryJob.prepared_pose,null);
    assert.equal(ordinaryJob.idle_video,null);
    assert.equal(ordinaryJob.chunks[0].render.continues_previous_pose,true);
    const back=await send(middle?1:3);
    await page.waitForFunction(()=>{
      const v=document.querySelector('#video');return !v.hidden&&!v.paused&&v.currentTime>=.2;
    },{}, {timeout:45000});
    await page.screenshot({path:path.join(folder,'return-from-stopped-pose.png')});
    const backJob=await finished(back);
    const movementMetrics=await page.locator('#metrics').textContent();
    assert.equal(backJob.prepared_pose,middle?'near':'base');
    assert.equal(backJob.chunks[0].render.motion_source,'reviewed_prepared_transition');
    assert.ok(Math.abs(backJob.chunks[0].render.transition_start_s-(middle?stopped.source_time_s:3-stopped.source_time_s))<.06);
    assert.equal(backJob.idle_video,middle?'/idle/near.mp4':'/idle/fullbody.mp4');
    assert.deepEqual(errors,[]);
    const result={request,stopped,approachState:(await getJob(approach)).state,
      ordinary:ordinaryJob,return:backJob,pageErrors:errors,
      stopAt,nextAction:middle?'continue':'return',ordinaryMetrics,movementMetrics,
      scope:'Synthetic ASR/planner. Actual CPU speech, GPU video, browser playback and authenticated cancellation.'};
    fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({stopped,approachState:result.approachState,
      ordinary:ordinaryJob.state,return:backJob.state,returnOffset:backJob.chunks[0].render.transition_start_s,pageErrors:errors}));
  }finally{
    await browser.close();
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true}));
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
