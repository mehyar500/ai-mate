// Actual isolated engine and browser playback; silent synthetic microphone.
// Typed inputs exercise Text/Voice/Video and navigation, not physical acoustics.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const label=process.argv[2];assert.match(label||'',/^[a-z0-9-]{1,32}$/);assert.ok(!process.argv[3]);
const folder=path.resolve(__dirname,'../generated/local-app/audit/voice-video-qualification-'+label);
assert.ok(fs.existsSync(path.join(folder,'fixtures.json')),'Start an isolated qualification server first.');
assert.ok(!fs.existsSync(path.join(folder,'mode-review.json')),'Preserve existing evidence.');
async function main(){
  const browser=await chromium.launch({headless:true});
  const rows=[],errors=[];let complete=false;
  try{
    const page=await browser.newPage({viewport:{width:390,height:844}});
    page.on('pageerror',e=>errors.push(e.message));
    await page.addInitScript(()=>{
      window.modeTest={streams:[],audioEvents:[],videoEvents:[]};
      navigator.mediaDevices.getUserMedia=async constraints=>{
        if(constraints.video)throw Error('Camera must remain off.');
        const context=new AudioContext(),destination=context.createMediaStreamDestination();
        await context.resume();window.modeTest.streams.push({context,stream:destination.stream});
        return destination.stream;
      };
      document.addEventListener('DOMContentLoaded',()=>{
        for(const id of ['audio','video'])for(const type of ['playing','ended','error']){
          document.getElementById(id).addEventListener(type,()=>{
            const el=document.getElementById(id);
            window.modeTest[id+'Events'].push({type,time:el.currentTime,muted:el.muted,volume:el.volume});
          });
        }
      });
    });
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled,{},{timeout:90000});
    const token=(await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json()).token;
    async function turn(name,mode,text,expected){
      await page.evaluate(()=>{window.modeTest.audioEvents=[];window.modeTest.videoEvents=[];});
      const submitted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/turn');
      if(mode==='text'){
        await page.locator('#message').fill(text);await page.locator('#send').click();
      }else{
        if(await page.locator('#call-composer').isHidden())await page.locator('#call-type').click();
        await page.locator('#call-message').fill(text);await page.locator('#call-send').click();
      }
      const response=await submitted;assert.equal(response.status(),202);
      const {id}=await response.json();assert.match(id,/^[a-f0-9]{32}$/);
      let job;const deadline=Date.now()+45000;
      do{
        job=await (await page.request.get('http://127.0.0.1:8766/api/jobs/'+id,{headers:{'X-Local-Token':token}})).json();
        if(['done','error','cancelled'].includes(job.state))break;
        await page.waitForTimeout(50);
      }while(Date.now()<deadline);
      assert.equal(job.state,'done',name);assert.equal(job.action,expected.action||'none');assert.equal(job.presentation,mode);
      if(expected.hint)assert.match(job.text,/Switch to Video/);
      if(expected.contains)assert.match(job.text,new RegExp(expected.contains,'i'));
      if(expected.noHint)assert.doesNotMatch(job.text,/Switch to Video/);
      if(mode==='text')assert.equal(job.chunks.length,0);
      else{
        assert.ok(job.chunks.length>0);
        assert.ok(job.chunks.every(c=>mode==='video'?Boolean(c.video):!c.video));
        await page.waitForFunction(()=>document.querySelector('#audio').ended,{},{timeout:20000});
        await page.waitForFunction(()=>document.querySelector('#call-state').textContent==='Listening',{},{timeout:10000});
        const events=await page.evaluate(()=>window.modeTest.audioEvents);
        assert.ok(events.some(e=>e.type==='playing'&&!e.muted&&e.volume>0));
        assert.ok(events.some(e=>e.type==='ended'&&e.time>0));
        assert.ok(await page.locator('#end-call').isVisible());
      }
      rows.push({case:name,mode,prompt:text,job,media:await page.evaluate(()=>({audio:window.modeTest.audioEvents,video:window.modeTest.videoEvents}))});
      fs.writeFileSync(path.join(folder,'mode-review.json'),JSON.stringify({complete:false,rows,errors},null,2)+'\n');
      console.log(JSON.stringify({case:name,mode,action:job.action,reply:job.text}));
    }
    await page.locator('#mode-text').click();
    await turn('text_movement','text','Could you wave hello?',{hint:true});
    await page.locator('#mode-voice').click();
    await turn('voice_movement','voice','Could you come closer?',{hint:true});
    const captures=await page.evaluate(()=>window.modeTest.streams.length);
    await page.locator('#mode-text').click();
    assert.ok(await page.locator('#active-call').isVisible());
    await turn('text_during_call','text',"What is my dog's name?",{contains:'Maple'});
    assert.ok(await page.locator('#active-call').isVisible());
    await page.locator('#return-call').click();
    assert.equal(await page.evaluate(()=>window.modeTest.streams.length),captures);
    await turn('voice_negation','voice','Please do not. Wave.',{noHint:true});
    await page.locator('#mode-video').click();
    await turn('video_movement','video','Wave hello.',{action:'wave',noHint:true});
    await page.locator('#mode-text').click();
    assert.ok(await page.locator('#active-call').isVisible());
    await turn('text_movement_during_video','text','Would you step back?',{hint:true});
    await page.locator('#return-call').click();
    await page.locator('#end-call').click();
    assert.ok(await page.locator('#active-call').isHidden());
    assert.ok(await page.evaluate(()=>window.modeTest.streams.every(x=>x.stream.getTracks().every(t=>t.readyState==='ended'))));
    assert.deepEqual(errors,[]);complete=true;
  }finally{
    await browser.close();
    fs.writeFileSync(path.join(folder,'mode-review.json'),JSON.stringify({complete,rows,errors,
      scope:'Six real engine turns, silent synthetic mic, actual Chromium audio/video playback. Navigation/mode honesty only; not physical speech, public network or 30-minute qualification.'},null,2)+'\n');
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true,turns:rows.length}));
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
