// Synthetic transport instrumentation. This page never captures a microphone.
let token, peer, context, analyser, monitorGain, jitter_ms;
const video=document.getElementById('video'), status=document.getElementById('status');
window.rtcBench={connected:false,transport:'webrtc',frames:[],audio:[],errors:[],turn:null,jitterTargets:[]};
const post=async(path,body={})=>{
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Local-Token':token},body:JSON.stringify(body)});
  const result=await response.json();if(!response.ok)throw Error(result.error);return result;
};
const gathered=()=>new Promise((resolve,reject)=>{
  if(peer.iceGatheringState==='complete')return resolve();
  const timeout=setTimeout(()=>{peer.removeEventListener('icegatheringstatechange',change);reject(Error('ICE gathering timed out'));},10000);
  function change(){if(peer.iceGatheringState==='complete'){clearTimeout(timeout);peer.removeEventListener('icegatheringstatechange',change);resolve();}}
  peer.addEventListener('icegatheringstatechange',change);
});
document.getElementById('connect').onclick=async()=>{
  try{
    context=new AudioContext();await context.resume();
    ({token,jitter_ms}=await (await fetch('/bootstrap')).json());
    peer=new RTCPeerConnection({iceServers:[]});
    peer.addTransceiver('video',{direction:'recvonly'});peer.addTransceiver('audio',{direction:'recvonly'});
    const stream=new MediaStream();video.srcObject=stream;
    peer.ontrack=event=>{
      if(jitter_ms!==null&&'jitterBufferTarget' in event.receiver)event.receiver.jitterBufferTarget=jitter_ms;
      window.rtcBench.jitterTargets.push({kind:event.track.kind,supported:'jitterBufferTarget' in event.receiver,value:event.receiver.jitterBufferTarget??null});
      stream.addTrack(event.track);
      if(event.track.kind==='audio'){
        analyser=context.createAnalyser();analyser.fftSize=512;
        const source=context.createMediaStreamSource(new MediaStream([event.track]));
        monitorGain=context.createGain();monitorGain.gain.value=0;
        source.connect(analyser);analyser.connect(monitorGain);monitorGain.connect(context.destination);
      }
    };
    peer.onconnectionstatechange=()=>{status.textContent=peer.connectionState;window.rtcBench.connected=peer.connectionState==='connected';};
    await peer.setLocalDescription(await peer.createOffer());await gathered();
    const answer=await post('/offer',{type:peer.localDescription.type,sdp:peer.localDescription.sdp});
    await peer.setRemoteDescription(answer);await video.play();
    const canvas=document.createElement('canvas');canvas.width=384;canvas.height=576;
    const draw=canvas.getContext('2d',{willReadFrequently:true});
    const frame=(_now,meta)=>{
      const at=performance.now();draw.drawImage(video,0,0,384,576);
      const rgb=draw.getImageData(8,568,1,1).data;
      const marked=rgb[1]>200&&rgb[2]<60;
      window.rtcBench.frames.push({at,mediaTime:meta.mediaTime,rtpTimestamp:meta.rtpTimestamp,marked});
      const turn=window.rtcBench.turn;
      if(turn&&marked&&turn.firstVideo===null){turn.firstVideo=at;turn.firstMediaTime=meta.mediaTime;}
      if(turn&&marked&&meta.mediaTime-turn.firstMediaTime>=.04&&turn.firstAdvancingVideo===null)turn.firstAdvancingVideo=at;
      video.requestVideoFrameCallback(frame);
    };
    video.requestVideoFrameCallback(frame);
    const samples=new Float32Array(512);
    const inspect=()=>{
      if(analyser){
        analyser.getFloatTimeDomainData(samples);let sum=0,peak=0;
        for(const value of samples){sum+=value*value;peak=Math.max(peak,Math.abs(value));}
        const rms=Math.sqrt(sum/samples.length),at=performance.now();
        window.rtcBench.audio.push({at,rms,peak});
        const turn=window.rtcBench.turn;if(turn&&rms>.006&&turn.firstAudio===null)turn.firstAudio=at;
      }
      if(peer.connectionState!=='closed')requestAnimationFrame(inspect);
    };inspect();
  }catch(error){window.rtcBench.errors.push(error.message);status.textContent=error.message;}
};
window.runRtcFixture=async fixture=>{
  const turn={started:performance.now(),firstVideo:null,firstAdvancingVideo:null,firstAudio:null};window.rtcBench.turn=turn;
  const result=await post('/run',{fixture});Object.assign(turn,result);return result;
};
window.rtcResults=()=>post('/results');
window.finishRtc=async()=>{const stats=[];for(const value of (await peer.getStats()).values())if(['inbound-rtp','codec'].includes(value.type))stats.push(value);await post('/done');peer.close();return stats;};
