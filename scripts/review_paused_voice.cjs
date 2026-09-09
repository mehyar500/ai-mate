// Fixed neutral, paused speech through the real browser microphone and call.
// Only the disposable benchmark on 8766; simulated AEC is not an acoustic test.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
const label=process.argv[2];assert.match(label||'',/^[a-z0-9-]{1,32}$/);
const root=path.resolve(__dirname,'..'),audit=path.join(root,'generated/local-app/audit');
const folder=path.join(audit,'voice-video-qualification-'+label);
const source=path.join(audit,'asr-calls-challenge');
const fixtures=JSON.parse(fs.readFileSync(path.join(source,'fixtures.json')))
  .filter(s=>['paused_negation','paused_correction'].includes(s.case));
assert.equal(fixtures.length,6);
assert.ok(fs.existsSync(path.join(folder,'benchmark-settings.json')));
assert.ok(!fs.existsSync(path.join(folder,'paused-results.json')));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
  const browser=await chromium.launch({headless:true});
  const rows=[],errors=[],requests=[];let current=null;
  const retained=path.join(folder,'retained-media');fs.mkdirSync(retained,{recursive:true});
  try{
    const page=await browser.newPage({viewport:{width:716,height:854}});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('response',r=>{
      const endpoint=new URL(r.url()).pathname;
      if(!['/api/audio','/api/cancel'].includes(endpoint))return;
      const row=current;
      const pending=(async()=>{
        const body=await r.json();
        const event={endpoint,status:r.status(),at_ms:Date.now(),body};
        if(endpoint==='/api/cancel')event.request=r.request().postDataJSON();
        if(endpoint==='/api/audio'&&row){
          const raw=r.request().postDataBuffer();
          const name=row.case+'-submitted-'+row.requests.filter(e=>e.endpoint==='/api/audio').length+'.wav';
          assert.ok(raw&&raw.length<=6000000);fs.writeFileSync(path.join(folder,name),raw);
          event.input_file=name;event.input_sha256=hash(raw);
        }
        if(row)row.requests.push(event);
      })().catch(()=>errors.push('Could not read benchmark response'));
      requests.push(pending);
    });
    await page.addInitScript(()=>{
      navigator.mediaDevices.getUserMedia=async constraints=>{
        if(constraints.video!==false)throw Error('Camera is not part of this test');
        const context=new AudioContext();await context.resume();
        const destination=context.createMediaStreamDestination();
        const track=destination.stream.getAudioTracks()[0],settings=track.getSettings.bind(track);
        track.getSettings=()=>({...settings(),echoCancellation:true});
        window.feedPausedSpeech=async encoded=>{
          const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
          const buffer=await context.decodeAudioData(bytes.buffer);
          const player=context.createBufferSource();player.buffer=buffer;player.connect(destination);
          const started=Date.now();
          await new Promise(resolve=>{player.onended=resolve;player.start();});
          player.disconnect();return {started,duration_s:buffer.duration};
        };
        return destination.stream;
      };
    });
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
    const bootstrap=await (await page.request.get('http://127.0.0.1:8766/api/bootstrap')).json();
    const headers={'X-Local-Token':bootstrap.token};
    assert.equal(bootstrap.ready,true);
    await page.locator('#join-call').click();
    await page.waitForFunction(()=>typeof window.feedPausedSpeech==='function');
    await page.evaluate(()=>{
      window.pausedEvents=[];
      for(const id of ['audio','video'])for(const type of ['playing','ended','waiting','error']){
        const el=document.getElementById(id);
        el.addEventListener(type,()=>window.pausedEvents.push({id,type,at_ms:Date.now(),time_s:el.currentTime,muted:el.muted,volume:el.volume}));
      }
    });
    for(const fixture of fixtures){
      assert.match(fixture.name,/^[a-z_]+-paused_(negation|correction)$/);
      const wav=fs.readFileSync(path.join(source,fixture.name+'.wav'));assert.equal(hash(wav),fixture.sha256);
      const row={case:fixture.name,expected:fixture.expected,source_sha256:fixture.sha256,requests:[],jobs:[]};
      current=row;await page.waitForTimeout(650);
      await page.evaluate(()=>{window.pausedEvents=[];});
      row.input=await page.evaluate(encoded=>window.feedPausedSpeech(encoded),wav.toString('base64'));
      // Keep observing beyond the entire source utterance and all split replies.
      const deadline=Date.now()+60000;let stableSince=null;
      while(Date.now()<deadline){
        await Promise.all(requests);
        const ids=row.requests.filter(r=>r.endpoint==='/api/audio'&&r.status===202).map(r=>r.body.id);
        row.jobs=await Promise.all(ids.map(async id=>(await page.request.get('http://127.0.0.1:8766/api/jobs/'+id,{headers})).json()));
        const idle=await page.evaluate(()=>document.querySelector('#video').hidden&&document.querySelector('#stop').hidden);
        const complete=ids.length&&row.jobs.every(j=>['done','cancelled','failed'].includes(j.state));
        if(idle&&complete){stableSince??=Date.now();if(Date.now()-stableSince>=1500)break;}else stableSince=null;
        await page.waitForTimeout(100);
      }
      row.settled=Boolean(stableSince&&Date.now()-stableSince>=1500);
      row.events=await page.evaluate(()=>window.pausedEvents);
      row.notice=await page.locator('#notice').textContent();
      const finalJob=row.jobs.at(-1);
      row.failures=[];
      if(!row.settled)row.failures.push('did_not_settle');
      if(finalJob?.state!=='done'||finalJob?.action!=='none')row.failures.push('negated_movement_not_respected');
      if(fixture.case==='paused_negation'&&!/\b(?:do not|don.t)\b/i.test(finalJob?.user||''))row.failures.push('negation_prefix_lost');
      if(fixture.case==='paused_correction'&&!/actually/i.test(finalJob?.user||''))row.failures.push('correction_prefix_lost');
      row.retainedMedia=[];
      for(const job of row.jobs)for(const chunk of job.chunks||[]){
        const name=chunk.audio?.split('/').at(-1);
        if(!name)continue;assert.match(name,/^[a-f0-9]{32}-\d+\.wav$/);
        for(const media of [name,name.replace(/\.wav$/,'.mp4')]){
          if(fs.existsSync(path.join(folder,media))){fs.copyFileSync(path.join(folder,media),path.join(retained,media));row.retainedMedia.push(media);}
        }
      }
      rows.push(row);
      fs.writeFileSync(path.join(folder,'paused-results.json'),JSON.stringify({rows,errors,scope:'Six synthetic paused utterances, real browser capture/VAD/ASR/Cloudflare/Kokoro/MuseTalk/playback. AEC capability simulated; no physical audio qualification. Memory carries between emitted turns and scenarios.'},null,2)+'\n');
      console.log(JSON.stringify({case:row.case,settled:row.settled,jobs:row.jobs.map(j=>({user:j.user,action:j.action,state:j.state,text:j.text,pose:j.prepared_pose})),responses:row.requests.map(r=>({endpoint:r.endpoint,status:r.status})),notice:row.notice}));
      assert.ok(row.settled,'Call did not settle');
    }
    current=null;await page.locator('#end-call').click();await page.waitForTimeout(500);
    assert.deepEqual(errors,[]);
    assert.ok(rows.every(r=>r.failures.length===0),'Paused-speech failures recorded in paused-results.json');
  }finally{
    await Promise.all(requests);await browser.close();
    fs.writeFileSync(path.join(folder,'browser-done.json'),JSON.stringify({finished:true}));
  }
}
main().catch(e=>{console.error(e.name+': '+e.message);process.exitCode=1;});
