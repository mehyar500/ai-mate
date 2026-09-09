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
  const results=[],layouts=[];
  try{
    for(const mode of ['video','voice']){
      const context=await browser.newContext({viewport:{width:390,height:844}});
      const page=await context.newPage();
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      let captures=0;const typed=[];
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
        if(url.pathname==='/api/turn'){
          typed.push(route.request().postDataJSON());
          if(typed.length===1)return route.fulfill({status:503,json:{error:'Synthetic retry test.'}});
          return route.fulfill({json:{id:'synthetic-typed'}});
        }
        if(['/api/jobs/synthetic-reply','/api/jobs/synthetic-typed'].includes(url.pathname))return route.fulfill({json:{
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
      await page.locator('#message').fill('Keep my separate message draft.');
      await page.locator('#return-call').click();
      assert.ok(await page.locator('#captions').isVisible());
      assert.ok(await page.locator('#call-composer').isHidden());
      await page.locator('#call-type').click();
      await page.locator('#call-message').fill('Please step back.');
      await page.locator('#call-message').press('Enter');
      await page.waitForFunction(()=>document.querySelector('#notice').textContent==='Synthetic retry test.');
      assert.equal(await page.locator('#call-message').inputValue(),'Please step back.');
      assert.equal(await page.locator('#message').inputValue(),'Keep my separate message draft.');
      assert.equal(await page.locator('.conversation').getAttribute('data-mode'),mode);
      await page.locator('#call-send').click();
      await page.waitForFunction(()=>!document.querySelector('#captions').hidden);
      assert.equal(typed.length,2);assert.ok(typed.every(t=>t.text==='Please step back.'&&t.mode===mode));
      assert.equal(await page.locator('#call-message').inputValue(),'');
      assert.equal(await page.locator('#mic').getAttribute('aria-label'),'Mute microphone');
      await page.screenshot({path:path.join(folder,'call-'+mode+'-typed.png')});
      await page.locator('#call-message').fill('Unsent call draft.');
      await page.locator('#mode-text').click();
      assert.ok(await page.locator('#call-composer').isHidden());
      await page.locator('#return-call').click();
      assert.equal(await page.locator('#call-message').inputValue(),'Unsent call draft.');
      await page.locator('#call-message').press('Escape');
      assert.ok(await page.locator('#call-composer').isHidden());
      assert.equal(await page.locator('#call-type').getAttribute('aria-expanded'),'false');
      const media=await page.locator('#audio').evaluate(el=>({muted:el.muted,volume:el.volume,paused:el.paused,currentTime:el.currentTime}));
      assert.equal(media.muted,false);assert.ok(media.volume>0);
      await page.waitForFunction(()=>document.querySelector('#audio').ended,{},{timeout:15000});
      await page.waitForFunction(()=>document.querySelector('#captions').hidden);
      assert.equal(captures,1);
      await page.locator('#end-call').click();
      assert.ok(await page.locator('#captions').isHidden());
      assert.ok(await page.locator('#active-call').isHidden());
      assert.deepEqual(errors,[]);
      results.push({mode,captures,typed_submissions:typed.length,typed_call_routing:'passed',retry_draft_preservation:'passed',
        optional_input_navigation:'passed',caption_navigation:'passed',unmuted_audio_completion:'passed',end_call:'passed',
        limitations:'Synthetic capture/API, real Chromium media playback; not physical speaker or real backend latency.'});
      await context.close();
    }
    // Layout only: no microphone hardware, API inference or conversation data.
    for(const [width,height] of [[320,568],[390,844],[716,854],[812,375],[1280,720]]){
      const page=await browser.newPage({viewport:{width,height}});
      await page.route('**/microphone.mjs',route=>route.fulfill({contentType:'text/javascript',body:`
        export class Microphone {
          constructor(o){this.o=o;this.generation=0;this.enabled=false;}
          async start(){this.enabled=true;this.o.onState('listening');}
          stop(){this.enabled=false;this.generation++;this.o.onState('off');}
        }`}));
      await page.route('**/api/**',route=>{
        if(!['/api/bootstrap','/api/status'].includes(new URL(route.request().url()).pathname))throw Error('Unexpected layout API call');
        return route.fulfill({json:{app_version:'0.2',token:'synthetic-layout',ready:true,busy:false,
          visual_loaded:true,provider:'cloudflare',scene:'fullbody',idle_video:null,turns:[],facts:[],memory:''}});
      });
      await page.goto('http://127.0.0.1:8765/');
      await page.waitForFunction(()=>!document.querySelector('#join-call').disabled);
      await page.locator('#join-call').click();await page.locator('#call-type').click();
      const layout=await page.evaluate(()=>{
        const ids=['call-type','mic','end-call','call-send','call-composer','memory-toggle','mode-text','mode-voice','mode-video'];
        const bounds=Object.fromEntries(ids.map(id=>{const b=document.getElementById(id).getBoundingClientRect();return [id,{x:b.x,y:b.y,w:b.width,h:b.height}];}));
        return {bounds,width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth};
      });
      assert.equal(layout.overflow,false);
      for(const [id,b] of Object.entries(layout.bounds)){
        assert.ok(b.x>=0&&b.y>=0&&b.x+b.w<=width+.5&&b.y+b.h<=height+.5,id+' clipped');
        assert.ok(b.w>=44&&b.h>=44,id+' below touch target');
      }
      const form=layout.bounds['call-composer'];
      for(const id of ['call-type','mic','end-call']){
        const b=layout.bounds[id];
        assert.ok(form.x+form.w<=b.x||b.x+b.w<=form.x||form.y+form.h<=b.y||b.y+b.h<=form.y,id+' overlaps input');
      }
      if(width===716)await page.screenshot({path:path.join(folder,'call-typed-fullbody-desktop.png')});
      layouts.push({width,height,overflow:false,input_controls_overlap:false});
      await page.close();
    }
  }finally{await browser.close();}
  fs.writeFileSync(path.join(folder,'call-playback-review.json'),JSON.stringify(results,null,2)+'\n');
  fs.writeFileSync(path.join(folder,'call-typed-layout-review.json'),JSON.stringify(layouts,null,2)+'\n');
  console.log(JSON.stringify({results,layouts}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
