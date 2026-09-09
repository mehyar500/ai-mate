// Real local engine/MSE playback; only microphone input is synthetic.
// Run serve_phrase_benchmark.py first. Port 8766 has its own synthetic database.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const label=process.argv[2];
assert.ok(['whole','phrases','phrases-b16','whole-b16','phrases-approach','phrases-approach-quality','phrases-b4-approach','phrases-approach-prewarm','phrases-approach-primed'].includes(label));
const folder=path.resolve(__dirname,'../generated/local-app/audit/speech-'+label);
async function main(){
  const browser=await chromium.launch({headless:true});
  try{
    const context=await browser.newContext({viewport:{width:716,height:854}});
    const page=await context.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
      export class Microphone {
        constructor(o){this.options=o;this.enabled=false;}
        async start(){this.enabled=true;this.options.onState('listening');
          this.timer=setTimeout(()=>{if(this.enabled)this.options.onTurn(new Uint8Array([1,2,3]));},150);}
        stop(){clearTimeout(this.timer);this.enabled=false;this.options.onState('off');}
      }`}));
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    await page.evaluate(()=>{
      window.playbackEvidence={events:[],started:performance.now()};
      for(const id of ['audio','video']){
        const el=document.getElementById(id);
        for(const type of ['playing','ended','waiting','error'])el.addEventListener(type,()=>{
          window.playbackEvidence.events.push({id,type,at:(performance.now()-window.playbackEvidence.started)/1000,
            currentTime:el.currentTime,muted:el.muted,volume:el.volume});
        });
      }
    });
    const submitted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/audio');
    await page.locator('#join-call').click();
    const key=(await (await submitted).json()).id;
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    await page.waitForFunction(()=>window.playbackEvidence.events.some(e=>e.id==='video'&&e.type==='playing'),{}, {timeout:45000});
    await page.screenshot({path:path.join(folder,'first-playback.png')});
    let job; const deadline=Date.now()+60000;
    do{
      job=await (await page.request.get('http://127.0.0.1:8766/api/jobs/'+key,{headers:{'X-Local-Token':token}})).json();
      if(['done','failed','cancelled'].includes(job.state))break;
      await new Promise(resolve=>setTimeout(resolve,150));
    }while(Date.now()<deadline);
    assert.equal(job.state,'done',job.error);
    await page.evaluate(job=>{window.benchmarkJob=job;},job);
    await page.waitForFunction(()=>['video','audio'].every(id=>
      window.playbackEvidence.events.filter(e=>e.id===id&&e.type==='ended').length>=window.benchmarkJob.chunks.length),{}, {timeout:60000});
    const result=await page.evaluate(()=>({events:window.playbackEvidence.events,
      metrics:document.querySelector('#metrics').textContent,
      audio:{ended:document.querySelector('#audio').ended,muted:document.querySelector('#audio').muted},
      chunks:window.benchmarkJob.chunks.length,
      notice:document.querySelector('#notice')?.textContent||''}));
    result.label=label;result.pageErrors=errors;
    fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
    assert.deepEqual(errors,[]);
    assert.ok(result.events.some(e=>e.id==='audio'&&e.type==='playing'&&!e.muted&&e.volume>0));
    if(label.includes('approach')){
      assert.equal(job.prepared_pose,'near');
      assert.equal(job.chunks.filter(c=>c.render.motion_source==='reviewed_prepared_transition').length,1);
      assert.ok(job.chunks.slice(1).every(c=>c.render.motion_source==='prepared_listening_loop'));
    }
    await context.close();
  }finally{
    await browser.close();
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true}));
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
