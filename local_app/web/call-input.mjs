// Keep one interrupting utterance while the previous render releases its GPU.
// The caller supplies a call/microphone generation stamp; stale audio is dropped.
export function speechAccess({ready,enabled,mode,busy,playing,stopping,submitting,echoCancellation,settled,capturing}){
  const active=ready&&enabled&&mode!=='text';
  // Silence while the server prepares a reply is still the user's speaking time.
  // Without AEC, exclude playback and its existing acoustic-tail cooldown.
  const open=active&&!stopping&&!submitting&&(playing?echoCancellation:settled);
  return {canListen:active&&(capturing||open),canInterrupt:open&&(busy||playing)};
}

export function continueSpeech(previous,next){
  if(!previous?.raw||!next?.raw||previous.mode!==next.mode)return next;
  // Only our recorder's canonical mono PCM16 WAVs, never arbitrary file formats.
  const read=raw=>{
    if(!(raw instanceof ArrayBuffer)||raw.byteLength<44)throw Error('Could not combine that recording. Please repeat your sentence.');
    const v=new DataView(raw),word=at=>String.fromCharCode(...new Uint8Array(raw,at,4));
    const rate=v.getUint32(24,true),length=v.getUint32(40,true);
    if(word(0)!=='RIFF'||word(8)!=='WAVE'||word(12)!=='fmt '||word(36)!=='data'||
       v.getUint32(4,true)!==raw.byteLength-8||v.getUint32(16,true)!==16||v.getUint16(20,true)!==1||
       v.getUint16(22,true)!==1||v.getUint16(34,true)!==16||v.getUint16(32,true)!==2||
       v.getUint32(28,true)!==rate*2||rate<8000||rate>96000||length%2||length!==raw.byteLength-44)
      throw Error('Could not combine that recording. Please repeat your sentence.');
    return {rate,length};
  };
  const a=read(previous.raw),b=read(next.raw),length=a.length+b.length;
  if(a.rate!==b.rate)throw Error('Your microphone changed. Please repeat your sentence.');
  if(length>a.rate*2*30)throw Error('That thought is too long to combine. Please repeat it in a shorter sentence.');
  const raw=new ArrayBuffer(44+length),bytes=new Uint8Array(raw),view=new DataView(raw);
  bytes.set(new Uint8Array(previous.raw));bytes.set(new Uint8Array(next.raw,44),44+a.length);
  view.setUint32(4,36+length,true);view.setUint32(40,length,true);
  return {...next,raw};
}

export class CallInput {
  constructor({state,stop,submit,combine=continueSpeech,onError=()=>{},now=()=>performance.now(),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))}){
    Object.assign(this,{state,stop,submit,combine,onError,now,wait});this.pending=null;this.previous=null;
  }
  reset(){this.pending=null;this.previous=null;}
  dispatch(input){this.previous={stamp:this.state().stamp,input};return this.submit(input);}
  capturing(){
    if(this.pending&&this.pending.stamp!==this.state().stamp)this.reset();
    return Boolean(this.pending?.receiving);
  }
  speech(force=false){
    const state=this.state();
    if(this.pending||(!force&&!state.canInterrupt))return;
    const prefix=!force&&state.canContinue&&this.previous?.stamp===state.stamp?this.previous.input:null;
    const pending={stamp:state.stamp,receiving:true,failed:false,prefix};this.pending=pending;
    // stop() pauses playback synchronously, then preserves the displayed pose.
    pending.stopped=Promise.resolve(this.stop()).then(ok=>{if(ok===false)pending.failed=true;}).catch(()=>{pending.failed=true;});
  }
  async turn(raw,{interrupt=false}={}){
    // A short word can pass utterance validation without reaching early onset.
    // It still needs to stop playback before submitting, rather than be dropped.
    if(!this.pending&&(interrupt||this.state().canInterrupt))this.speech(interrupt);
    const pending=this.pending;
    if(!pending)return this.dispatch(raw);
    if(!pending.receiving)return; // Never queue a second utterance behind cleanup.
    pending.receiving=false;
    try{
      await pending.stopped;
      const deadline=this.now()+10000;
      while(this.pending===pending&&this.state().stamp===pending.stamp&&this.state().busy&&this.now()<deadline)
        await this.wait(25);
      if(this.pending!==pending||this.state().stamp!==pending.stamp)return;
      if(pending.failed||this.state().busy)throw Error('The previous reply is still stopping. Please speak again.');
      const input=pending.prefix?this.combine(pending.prefix,raw):raw;
      this.pending=null;
      return this.dispatch(input);
    }catch(error){if(this.pending===pending)this.onError(error);}
    finally{if(this.pending===pending)this.pending=null;}
  }
}
