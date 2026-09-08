// Local PCM capture. No browser speech service or microphone audio upload to an AI provider.
export function encodeWav(chunks, rate) {
  const count=chunks.reduce((n,c)=>n+c.length,0), out=new ArrayBuffer(44+count*2), view=new DataView(out);
  const word=(offset,text)=>{for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i));};
  word(0,'RIFF');view.setUint32(4,36+count*2,true);word(8,'WAVE');word(12,'fmt ');
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
  view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
  word(36,'data');view.setUint32(40,count*2,true);
  let i=44;for(const chunk of chunks)for(const sample of chunk){const x=Math.max(-1,Math.min(1,sample));view.setInt16(i,x<0?x*32768:x*32767,true);i+=2;}
  return out;
}

export class SpeechTurns {
  constructor(rate,onTurn,onSpeech=()=>{}){this.rate=rate;this.onTurn=onTurn;this.onSpeech=onSpeech;this.reset();}
  reset(){this.chunks=[];this.pre=[];this.preSamples=0;this.total=0;this.quiet=0;this.voiced=0;this.active=false;this.noise=.002;}
  push(chunk){
    let power=0;for(const x of chunk)power+=x*x;
    const rms=Math.sqrt(power/chunk.length), loud=rms>Math.max(.009,this.noise*3);
    if(!this.active){
      this.pre.push(chunk);this.preSamples+=chunk.length;
      while(this.preSamples>this.rate*.2&&this.pre.length>1)this.preSamples-=this.pre.shift().length;
      if(!loud){this.noise=.995*this.noise+.005*Math.min(rms,.01);return;}
      this.active=true;this.chunks=this.pre;this.total=this.preSamples;this.pre=[];this.preSamples=0;
    }else{this.chunks.push(chunk);this.total+=chunk.length;}
    this.quiet=loud?0:this.quiet+chunk.length;if(loud)this.voiced+=chunk.length;
    if(this.voiced>=this.rate*.12)this.onSpeech();
    if(this.quiet>=this.rate*.65||this.total>=this.rate*25){
      const chunks=this.chunks,valid=this.voiced>=this.rate*.16;this.reset();
      if(valid)this.onTurn(encodeWav(chunks,this.rate));
    }
  }
}

export class Microphone {
  constructor({onTurn,onState,canListen}){this.onTurn=onTurn;this.onState=onState;this.canListen=canListen;this.generation=0;this.enabled=false;this.pending=false;}
  async start(){
    if(this.enabled||this.pending)return;
    if(!globalThis.isSecureContext||!navigator.mediaDevices?.getUserMedia)throw Error('Microphone needs localhost or HTTPS and a supported browser. Text chat is available in the Text tab.');
    this.pending=true;const generation=++this.generation;this.onState('permission');
    let stream,context;
    try{
      stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
      if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
      context=new AudioContext();await context.resume();await context.audioWorklet.addModule('/recorder.js');
      if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());await context.close();return;}
      this.stream=stream;this.context=context;this.source=context.createMediaStreamSource(stream);
      this.worklet=new AudioWorkletNode(context,'local-recorder');
      this.turns=new SpeechTurns(context.sampleRate,raw=>{this.onState('processing');this.onTurn(raw);},()=>this.onState('hearing'));
      this.enabled=true;this.worklet.port.onmessage=event=>{
        if(!this.enabled)return;
        if(!this.canListen()){this.turns.reset();this.onState('paused');return;}
        if(!this.turns.active)this.onState('listening');
        this.turns.push(event.data);
      };
      stream.getAudioTracks()[0].onended=()=>{this.stop();this.onState('disconnected');};
      this.source.connect(this.worklet);this.worklet.connect(context.destination);this.onState('listening');
    }catch(error){
      stream?.getTracks().forEach(t=>t.stop());if(context&&context.state!=='closed')await context.close();
      if(generation!==this.generation)return;
      this.enabled=false;this.onState('off');
      throw Error(error.name==='NotAllowedError'?'Microphone permission was denied. Allow it in browser settings and tap Unmute to retry. Text chat is available in the Text tab.':error.name==='NotFoundError'?'No microphone found. Connect one and tap Unmute to retry, or open Text chat.':'Microphone could not start. Check your input device and tap Unmute to retry.');
    }finally{if(generation===this.generation)this.pending=false;}
  }
  stop(){
    this.generation++;this.pending=false;this.enabled=false;
    if(this.worklet){this.worklet.port.onmessage=null;this.worklet.disconnect();}
    this.source?.disconnect();this.stream?.getTracks().forEach(t=>{t.onended=null;t.stop();});
    if(this.context&&this.context.state!=='closed')this.context.close().catch(()=>{});
    this.stream=null;this.context=null;this.source=null;this.worklet=null;this.turns=null;this.onState('off');
  }
}
