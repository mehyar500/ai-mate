// Persistent WebRTC receiver, fixed retained speech, actual GPU frame generation.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const label=process.argv[2];assert.match(label,/^[a-z0-9-]{1,32}$/);assert.ok(!process.argv[3]);
const folder=path.resolve(__dirname,'../generated/local-app/audit/webrtc-'+label);
async function main(){
  const browser=await chromium.launch({headless:true,args:['--disable-features=WebRtcHideLocalIpsWithMdns']});
  const results={turns:[],pageErrors:[],scope:'Synthetic renderer-start to first decoded picture, advancing picture and audio. RTC pictures use a marker; MSE uses frame callbacks. No microphone, ASR, dialogue, TTS synthesis, public network, physical speakers or human perceptual acceptance.'};
  let page;
  try{
    page=await browser.newPage({viewport:{width:700,height:850}});page.on('pageerror',error=>results.pageErrors.push(error.message));
    await page.goto('http://127.0.0.1:8766/');
    const base='http://127.0.0.1:8766',bootstrap=await (await page.request.get(base+'/bootstrap')).json();
    const checks=[];
    for(const test of [
      {name:'missing-token',url:'/run',headers:{},body:{fixture:0},status:403},
      {name:'cross-origin',url:'/run',headers:{Origin:'https://example.invalid','X-Local-Token':bootstrap.token},body:{fixture:0},status:403},
      {name:'invalid-offer',url:'/offer',headers:{'X-Local-Token':bootstrap.token},body:{type:'offer',sdp:'invalid'},status:400},
      {name:'oversized',url:'/offer',headers:{'X-Local-Token':bootstrap.token},body:{type:'offer',sdp:'x'.repeat(33000)},status:400}
    ]){
      const response=await page.request.post(base+test.url,{headers:test.headers,data:test.body});assert.equal(response.status(),test.status,test.name);checks.push({name:test.name,status:response.status()});
    }
    results.signalingChecks=checks;
    if(bootstrap.transport==='webrtc'){
      const response=await page.request.post(base+'/run',{headers:{'X-Local-Token':bootstrap.token},data:{fixture:0}});
      assert.equal(response.status(),409);checks.push({name:'run-before-connected',status:response.status()});
    }
    await page.locator('#connect').click();
    await page.waitForFunction(()=>window.rtcBench.connected&&(window.rtcBench.transport==='mse'||document.querySelector('video').readyState>=2),{},{timeout:20000});
    results.transport=await page.evaluate(()=>window.rtcBench.transport);
    results.jitterTargets=await page.evaluate(()=>window.rtcBench.jitterTargets||[]);
    await page.waitForTimeout(2500); // Let the persistent stream exchange sender reports.
    for(let index=0;index<12;index++){
      if(results.transport==='webrtc')await page.waitForFunction(()=>window.rtcBench.frames.length&&window.rtcBench.frames.at(-1).marked===false);
      const info=await page.evaluate(fixture=>window.runRtcFixture(fixture),index%3);
      await page.waitForFunction(()=>window.rtcBench.turn.firstAdvancingVideo!==null&&window.rtcBench.turn.firstAudio!==null,{},{timeout:15000});
      const timing=await page.evaluate(()=>{const t=window.rtcBench.turn;return {firstVideo_s:(t.firstVideo-t.started)/1000,firstAdvancingVideo_s:(t.firstAdvancingVideo-t.started)/1000,firstAudio_s:(t.firstAudio-t.started)/1000};});
      if(index<3)await page.locator('video').screenshot({path:path.join(folder,`received-${info.case}.png`)});
      await page.waitForTimeout(Math.ceil(info.duration_s*1000)+600);
      const server=await page.evaluate(()=>window.rtcResults());const row=server.rows.at(-1);
      assert.ok(row.finished,'Reply must finish');assert.ok(!row.error,JSON.stringify(row.error));
      const metrics=await page.evaluate(()=>{
        const t=window.rtcBench.turn,frames=window.rtcBench.frames.filter(f=>f.at>=t.started&&f.marked),audio=window.rtcBench.audio.filter(a=>a.at>=t.started);
        return {markedFrames:frames.length,longFrameGaps:frames.slice(1).filter((f,i)=>f.at-frames[i].at>100).length,
          maxAudioRms:Math.max(...audio.map(a=>a.rms)),maxAudioPeak:Math.max(...audio.map(a=>a.peak))};
      });
      const result={...info,...timing,...metrics,server:row};results.turns.push(result);console.log(JSON.stringify({case:info.case,...timing,underflows:row.underflows,frames:metrics.markedFrames}));
      assert.equal(row.underflows,0);assert.ok(metrics.markedFrames>0&&metrics.maxAudioRms>.006);
      await page.evaluate(()=>{window.rtcBench.turn=null;});
    }
    if(results.transport==='webrtc'){
      results.cancelledReply=await page.evaluate(()=>window.runRtcFixture(0));
      await page.waitForFunction(()=>window.rtcBench.turn.firstAdvancingVideo!==null);
    }
    results.receiverStats=await page.evaluate(()=>window.finishRtc());
    results.errors=await page.evaluate(()=>window.rtcBench.errors);
    assert.deepEqual(results.pageErrors,[]);assert.deepEqual(results.errors,[]);
    if(results.transport==='webrtc'){
      const inbound=results.receiverStats.filter(s=>s.type==='inbound-rtp');
      const video=inbound.find(s=>s.kind==='video'),codec=results.receiverStats.find(s=>s.id===video?.codecId);
      assert.equal(codec?.mimeType,'video/H264','Validate the negotiated codec, not the requested preference');
      for(const stat of inbound)assert.equal(stat.packetsLost,0);
      assert.equal(video.framesDropped,0);assert.equal(video.freezeCount,0);
    }
    results.complete=true;
  }catch(error){results.failure=error.message;throw error;}
  finally{
    if(page)results.capture=await page.evaluate(()=>({frames:window.rtcBench?.frames||[],audio:window.rtcBench?.audio||[]})).catch(()=>null);
    fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify(results,null,2)+'\n');await browser.close();
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
