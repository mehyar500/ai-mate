// Real ASR, hosted plans, CPU TTS and GPU video. Only physical capture is replaced.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const trial=process.argv[2];
assert.ok(['baseline','revised','selected'].includes(trial));
const folder=path.resolve(__dirname,'../generated/local-app/audit/voice-video-'+trial);
async function main(){
  const browser=await chromium.launch({headless:true});
  const results=[];
  try{
    const context=await browser.newContext({viewport:{width:716,height:854}});
    const page=await context.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
      export class Microphone {
        constructor(o){this.options=o;this.enabled=false;}
        async start(){this.enabled=true;this.options.onState('listening');
          window.benchmarkEmit=(encoded)=>{if(!this.enabled)throw Error('Call is stopped');
            this.options.onTurn(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)));};}
        stop(){this.enabled=false;this.options.onState('off');}
      }`}));
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    await page.locator('#join-call').click();
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    for(const fixture of JSON.parse(fs.readFileSync(path.join(folder,'fixtures.json')))){
      await page.evaluate(()=>{
        window.playbackEvidence={events:[],started:performance.now()};
        if(!window.benchmarkObserved){
          for(const id of ['audio','video'])for(const type of ['playing','ended','waiting','error']){
            const el=document.getElementById(id);
            el.addEventListener(type,()=>window.playbackEvidence.events.push({id,type,
              at:(performance.now()-window.playbackEvidence.started)/1000,
              currentTime:el.currentTime,muted:el.muted,volume:el.volume}));
          }
          window.benchmarkObserved=true;
        }
      });
      const submitted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/audio');
      await page.evaluate(encoded=>window.benchmarkEmit(encoded),fs.readFileSync(path.join(folder,fixture.case+'.wav')).toString('base64'));
      const response=await submitted;assert.equal(response.status(),202);
      const key=(await response.json()).id;
      let job;const deadline=Date.now()+90000;
      do{
        job=await (await page.request.get('http://127.0.0.1:8766/api/jobs/'+key,{headers:{'X-Local-Token':token}})).json();
        if(['done','failed','cancelled'].includes(job.state))break;
        await new Promise(resolve=>setTimeout(resolve,100));
      }while(Date.now()<deadline);
      assert.equal(job.state,'done',job.error);
      await page.waitForFunction(count=>['video','audio'].every(id=>
        window.playbackEvidence.events.filter(e=>e.id===id&&e.type==='ended').length>=count),job.chunks.length,{timeout:60000});
      const result=await page.evaluate(()=>({events:window.playbackEvidence.events,
        metrics:document.querySelector('#metrics').textContent,
        audio:{ended:document.querySelector('#audio').ended,muted:document.querySelector('#audio').muted}}));
      Object.assign(result,{case:fixture.case,expected:fixture.prompt,transcribed:job.user,reply:job.text,
        engine:job.metrics,action:job.action,prepared_pose:job.prepared_pose,pageErrors:[...errors]});
      results.push(result);
      fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify(results,null,2)+'\n');
      await page.screenshot({path:path.join(folder,fixture.case+'.png')});
      console.log(JSON.stringify(result));
      assert.deepEqual(errors,[]);
      assert.ok(result.events.some(e=>e.id==='audio'&&e.type==='playing'&&!e.muted&&e.volume>0));
      if(trial!=='baseline')assert.equal(result.events.filter(e=>e.id==='audio'&&e.type==='ended').length,job.chunks.length);
      if(trial==='selected')assert.match(result.metrics,/Buffer waits: 0/);
      if(fixture.case==='memory')assert.match(job.text,/Maple/i);
      if(fixture.case==='approach')assert.equal(job.prepared_pose,'near');
      await page.waitForFunction(()=>!document.querySelector('#end-call').disabled);
    }
    await context.close();
  }finally{
    await browser.close();
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true,turns:results.length}));
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
