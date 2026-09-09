// Review-page UI/decoded-audio checks. Serve only its synthetic audit folder on
// localhost:8767; run after call timing to avoid competing media playback.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const trial=process.argv[2],label=process.argv[3];
assert.ok(['qualification','soak'].includes(trial));assert.match(label,/^[a-z0-9-]{1,32}$/);
const port=Number(process.argv[4]||8767);assert.ok([8767,8768,8769].includes(port));assert.ok(!process.argv[5]);
const run=`voice-video-${trial}-${label}`;
const folder=path.resolve(__dirname,'../generated/local-app/audit',run);

async function main(){
  const browser=await chromium.launch({headless:true});
  const errors=[],consoleErrors=[];
  try{
    const page=await browser.newPage({viewport:{width:1000,height:850},acceptDownloads:true});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});
    await page.goto(`http://127.0.0.1:${port}/review.html`);
    const report=await page.locator('#report').evaluate(el=>JSON.parse(el.textContent));
    assert.equal(report.run,run);assert.equal(await page.locator('#clips option').count(),report.items.length);
    await page.waitForFunction(()=>document.querySelector('#video').readyState>=2);
    assert.equal(await page.locator('#reviewed').isChecked(),false);
    await page.locator('#next-frame').click();
    await page.waitForFunction(()=>document.querySelector('#frame-info').textContent.startsWith('Frame 2/'));
    await page.locator('#back-frame').click();
    await page.waitForFunction(()=>document.querySelector('#frame-info').textContent.startsWith('Frame 1/'));
    const audio=await page.evaluate(async()=>{
      const video=document.querySelector('#video');video.currentTime=0;video.muted=false;video.volume=1;
      const context=new AudioContext(),source=context.createMediaElementSource(video),analyser=context.createAnalyser();
      analyser.fftSize=2048;source.connect(analyser);analyser.connect(context.destination);await context.resume();
      const samples=new Float32Array(2048),values=[];await video.play();
      const began=performance.now();
      while(performance.now()-began<1000&&!video.ended){
        analyser.getFloatTimeDomainData(samples);let square=0,peak=0;
        for(const value of samples){square+=value*value;peak=Math.max(peak,Math.abs(value));}
        values.push({rms:Math.sqrt(square/samples.length),peak});await new Promise(r=>setTimeout(r,20));
      }
      video.pause();source.disconnect();analyser.disconnect();await context.close();
      return {samples:values.length,maxRms:Math.max(...values.map(v=>v.rms)),maxPeak:Math.max(...values.map(v=>v.peak)),
        scope:'Decoded MP4 audio reached an AudioContext destination in headless Chromium. No physical speaker, microphone, listening or perceptual lip-sync claim.'};
    });
    assert.ok(audio.samples>=10&&audio.maxRms>.005,'No decoded audio signal at the browser destination');
    await page.locator('#note').fill('Automated review UI fixture; no perceptual acceptance.');
    await page.locator('#flag').click();
    const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();
    const download=await downloadPromise;await download.saveAs(path.join(folder,'review-ui-notes.json'));
    const notes=JSON.parse(fs.readFileSync(path.join(folder,'review-ui-notes.json'),'utf8'));
    assert.equal(notes.run,run);assert.equal(Object.values(notes.notes)[0].reviewed,false);
    assert.equal(Object.values(notes.notes)[0].audioHeard,false);
    assert.equal(Object.values(notes.notes)[0].flags.length,1);
    await page.locator('#next').click();await page.waitForFunction(()=>document.querySelector('#clips').value==='1');
    await page.waitForFunction(()=>document.querySelector('#video').readyState>=2);
    await page.screenshot({path:path.join(folder,'review-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,
      buttons:[...document.querySelectorAll('button')].map(el=>({id:el.id,height:el.getBoundingClientRect().height}))}));
    assert.ok(layout.scroll<=layout.width);assert.ok(layout.buttons.every(b=>b.height>=44));
    await page.screenshot({path:path.join(folder,'review-mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(consoleErrors,[]);
    const result={clips:report.items.length,frameStepping:true,export:true,defaultUnreviewed:true,audio,layout,errors,consoleErrors};
    fs.writeFileSync(path.join(folder,'review-ui-results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  }finally{await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
