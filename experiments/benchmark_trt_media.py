"""Compare real neutral speech/motion renders using Torch and the local TRT VAE."""
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'.cache/tensorrt-deps'))
from local_app.visual import PortraitRenderer
from scripts.trt_vae_runtime import ExperimentalDecoder


def main():
    folder=ROOT/'generated/local-app/audit/visual-trt-media'
    folder.mkdir(exist_ok=False)
    renderer=PortraitRenderer(); torch=renderer.torch; cv=renderer.cv; np=renderer.np
    eager=renderer.decode_prediction
    decoder=ExperimentalDecoder(torch,ROOT/'generated/local-app/audit/visual-trt-fp16')
    assets=ROOT/'generated/local-app'
    renderer.prepare('fullbody')
    source_names=['idle-fullbody.mp4','idle-near.mp4','performance-closer.mp4','performance-farther.mp4','performance-wave.mp4']
    renderer.prime_motion([assets/name for name in source_names],threading.Event())
    fixtures=ROOT/'generated/local-app/audit/voice-video-qualification-temporal128'
    jobs={r['case']:r['job'] for r in json.loads((fixtures/'qualification.json').read_text())['results']}
    cases=[('greeting','idle-fullbody.mp4',True),('description','idle-near.mp4',True),
           ('approach','performance-closer.mp4',False),('wave','performance-wave.mp4',False)]
    rows=[]
    for index,(case,source,loop) in enumerate(cases):
        audio=fixtures/'retained-media'/jobs[case]['chunks'][0]['audio'].rsplit('/',1)[-1]
        row={'case':case,'source':source,'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest()}
        for name in (['torch','trt'] if index%2==0 else ['trt','torch']):
            renderer.decode_prediction=eager if name=='torch' else decoder
            renderer.decoder_backend='torch' if name=='torch' else 'tensorrt-experiment'
            row[name]=renderer.render(audio,folder/(case+'-'+name+'.mp4'),threading.Event(),'fullbody',streaming=True,
                                      motion_path=assets/source,loop_motion=loop,reuse_motion=True)
        a=cv.VideoCapture(str(folder/(case+'-torch.mp4'))); b=cv.VideoCapture(str(folder/(case+'-trt.mp4')))
        deltas=[]; maximum=0; worst=None
        try:
            while True:
                ok,x=a.read(); other,y=b.read()
                if ok!=other:raise RuntimeError('Different decoded frame counts.')
                if not ok:break
                difference=np.abs(x.astype(np.float32)-y)
                score=float(difference.mean()); deltas.append(score); maximum=max(maximum,float(difference.max()))
                if worst is None or score>worst[0]:worst=(score,len(deltas)-1,x,y)
        finally:a.release(); b.release()
        if not deltas:raise RuntimeError('No rendered frames.')
        cv.imwrite(str(folder/(case+'-worst-pair.jpg')),np.hstack((worst[2],worst[3])))
        row['frame_comparison']={'frames':len(deltas),'whole_frame_mean_mae_255':float(np.mean(deltas)),
                                 'worst_frame_mae_255':max(deltas),'max_channel_difference_255':maximum,
                                 'worst_frame':worst[1],'per_frame_mae_255':deltas}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='frame_comparison'}),flush=True)
    # Test every partial batch size against eager decoding; padding cannot change
    # a sample's result or leak a prior sample through the reusable output buffer.
    with torch.inference_mode():
        latent=renderer.latent.expand(8,-1,-1,-1).clone().contiguous(memory_format=torch.channels_last)
        condition=torch.zeros((8,50,384),device='cuda',dtype=renderer.dtype)+renderer.pe
        prediction=renderer.unet(latent,torch.tensor(0,device='cuda'),encoder_hidden_states=condition).sample
        partial=[]
        pixel=lambda value:((value.float()/2+.5).clamp(0,1)*255).round()
        for count in range(1,9):
            expected=eager(prediction[:count]); actual=decoder(prediction[:count]); difference=(pixel(expected)-pixel(actual)).abs()
            partial.append({'batch':count,'finite':bool(torch.isfinite(actual).all().item()),
                            'pixel_mae_255':difference.mean().item(),'pixel_max_255':difference.max().item()})
    result={'cases':rows,'partial_batches':partial,'scope':'Four actual speech-driven renders with identical prepared source/audio, plus all partial batch sizes. Every output frame compared. Pixel closeness is not independent perceptual or physical-audio acceptance.'}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'partial_batches':partial,'all_frames':sum(r['frame_comparison']['frames'] for r in rows)}),flush=True)
    if not all(p['finite'] and p['pixel_mae_255']<.5 for p in partial):
        raise RuntimeError('Partial decoder output failed the comparison.')


if __name__=='__main__':main()
