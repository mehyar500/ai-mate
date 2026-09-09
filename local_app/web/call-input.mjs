// Keep one interrupting utterance while the previous render releases its GPU.
// The caller supplies a call/microphone generation stamp; stale audio is dropped.
export class CallInput {
  constructor({state,stop,submit,onError=()=>{},now=()=>performance.now(),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))}){
    Object.assign(this,{state,stop,submit,onError,now,wait});this.pending=null;
  }
  reset(){this.pending=null;}
  capturing(){
    if(this.pending&&this.pending.stamp!==this.state().stamp)this.reset();
    return Boolean(this.pending?.receiving);
  }
  speech(force=false){
    const state=this.state();
    if(this.pending||(!force&&!state.canInterrupt))return;
    const pending={stamp:state.stamp,receiving:true,failed:false};this.pending=pending;
    // stop() pauses playback synchronously, then preserves the displayed pose.
    pending.stopped=Promise.resolve(this.stop()).then(ok=>{if(ok===false)pending.failed=true;}).catch(()=>{pending.failed=true;});
  }
  async turn(raw,{interrupt=false}={}){
    // A short word can pass utterance validation without reaching early onset.
    // It still needs to stop playback before submitting, rather than be dropped.
    if(!this.pending&&(interrupt||this.state().canInterrupt))this.speech(interrupt);
    const pending=this.pending;
    if(!pending)return this.submit(raw);
    if(!pending.receiving)return; // Never queue a second utterance behind cleanup.
    pending.receiving=false;
    try{
      await pending.stopped;
      const deadline=this.now()+10000;
      while(this.pending===pending&&this.state().stamp===pending.stamp&&this.state().busy&&this.now()<deadline)
        await this.wait(25);
      if(this.pending!==pending||this.state().stamp!==pending.stamp)return;
      if(pending.failed||this.state().busy)throw Error('The previous reply is still stopping. Please speak again.');
      this.pending=null;
      return this.submit(raw);
    }catch(error){if(this.pending===pending)this.onError(error);}
    finally{if(this.pending===pending)this.pending=null;}
  }
}
