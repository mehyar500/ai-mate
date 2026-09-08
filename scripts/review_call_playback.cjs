// Synthetic browser check against the running local static UI. All APIs and
// microphone capture are intercepted: no private history or hardware capture.
// Requires Playwright on NODE_PATH and the explicitly generated audit fixtures.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const folder=path.resolve(__dirname,'../generated/local-app/audit');
const stem='flashhead-lite-performance-near-384x576-s4-cloud-aura1-normal';
const caption='The garden is quiet with birdsong. Flowers sway in the breeze.';
async function main(){
  for(const ext of ['mp4','wav'])assert.ok(fs.existsSync(path.join(folder,stem+'.'+ext)),'Generate the synthetic FlashHead fixture first.');
  const browser=await chromium.launch({headless:true});
  const results=[];
  try{
    for(const mode of ['video','voice']){
      const context=await browser.newContext({viewport:{width:390,height:844}});
      const page=await context.newPage();
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      let captures=0;
      await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
        export class Microphone {
          constructor(options){this.options=options;this.enabled=false;this.pending=false;}
          async start(){this.enabled=true;this.options.onState('listening');
            this.timer=setTimeout(()=>{if(this.enabled)this.options.onTurn(new Uint8Array([1,2,3]));},150);}
          stop(){clearTimeout(this.timer);this.enabled=false;this.options.onState('off');}
        }`}));
      await page.route('**/api/**',route=>{
        const url=new URL(route.request().url());
        if(['/api/bootstrap','/api/status'].includes(url.pathname))return route.fulfill({json:{
          app_version:'0.2',token:'synthetic-playback-only',ready:true,busy:false,visual_loaded:true,
          provider:'cloudflare',scene:'fullbody',idle_video:null,turns:[],facts:[],memory:''}});
        if(url.pathname==='/api/audio'){captures++;return route.fulfill({json:{id:'synthetic-reply'}});}
        if(url.pathname==='/api/jobs/synthetic-reply')return route.fulfill({json:{
          state:'done',scene:'fullbody',action:'none',presentation:mode,user:'Synthetic speech input',text:caption,
          metrics:{total_s:.1},chunks:[{text:caption,duration_s:5.76,audio:'/fixture.wav',
          ...(mode==='video'?{video:'/fixture.mp4'}:{})}]}});
        if(url.pathname==='/api/cancel')return route.fulfill({json:{ok:true}});
        throw Error('Unexpected API request '+url.pathname);
      });
      for(const [ext,mime] of [['mp4','video/mp4'],['wav','audio/wav']]){
        await page.route('**/fixture.'+ext,route=>route.fulfill({path:path.join(folder,stem+'.'+ext),contentType:mime}));
      }
      await page.goto('http://127.0.0.1:8765/');
      await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
      await page.locator('#memory-toggle').click();
      await page.locator('#show-captions').check();
      await page.locator('#close-settings').click();
      await page.locator(mode==='video'?'#join-call':'#mode-voice').click();
      await page.waitForFunction(()=>!document.querySelector('#captions').hidden);
      assert.equal(await page.locator('#captions').textContent(),caption);
      await page.screenshot({path:path.join(folder,'call-'+mode+'-captions.png')});
      await page.locator('#mode-text').click();
      assert.ok(await page.locator('#captions').isHidden());
      assert.ok(await page.locator('#composer').isVisible());
      await page.locator('#return-call').click();
      assert.ok(await page.locator('#captions').isVisible());
      const media=await page.locator('#audio').evaluate(el=>({muted:el.muted,volume:el.volume,paused:el.paused,currentTime:el.currentTime}));
      assert.equal(media.muted,false);assert.ok(media.volume>0);
      await page.waitForFunction(()=>document.querySelector('#audio').ended,{},{timeout:15000});
      await page.waitForFunction(()=>document.querySelector('#captions').hidden);
      assert.equal(captures,1);
      await page.locator('#end-call').click();
      assert.ok(await page.locator('#captions').isHidden());
      assert.ok(await page.locator('#active-call').isHidden());
      assert.deepEqual(errors,[]);
      results.push({mode,captures,caption_navigation:'passed',unmuted_audio_completion:'passed',end_call:'passed',
        limitations:'Synthetic capture/API, real Chromium media playback; not physical speaker or real backend latency.'});
      await context.close();
    }
  }finally{await browser.close();}
  fs.writeFileSync(path.join(folder,'call-playback-review.json'),JSON.stringify(results,null,2)+'\n');
  console.log(JSON.stringify(results));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
