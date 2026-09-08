"""Bounded non-explicit FlashHead Lite trial; no conversation or app selection.

Uses pinned upstream single-GPU code with optional imports/compile disabled by
config/flashhead-windows.patch. SDPA timings are not author Sage/compiled timings.
"""
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'.cache/local-poc/SoulX-FlashHead'
REVISION='9bc03de06bb0de82cd6bc477804512ae06144bf2'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=384)
    parser.add_argument('--height',type=int,default=576)
    parser.add_argument('--chunks',type=int,default=4)
    parser.add_argument('--reference',choices=['fullbody','performance-near'],default='fullbody')
    parser.add_argument('--steps',type=int,choices=[2,4],default=4)
    parser.add_argument('--audio',choices=['greeting','cloud-aura1-normal','kokoro-long'],default='greeting')
    args=parser.parse_args()
    if any(n<256 or n>576 or n%32 for n in (args.width,args.height)) or not 2<=args.chunks<=32:
        parser.error('Use 256–576px dimensions divisible by 32 and two to 32 chunks (at most 30.72s).')
    actual=subprocess.check_output(['git','-C',str(CODE),'rev-parse','HEAD'],text=True).strip()
    if actual!=REVISION:
        raise RuntimeError('Unexpected FlashHead source revision.')
    sys.path[:0]=[str(ROOT/'.cache/flashhead-deps'),str(CODE)]
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.chdir(CODE)
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    import torch
    import flash_head.inference as inference
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False
    torch.cuda.reset_peak_memory_stats()
    inference.infer_params['height']=args.height
    inference.infer_params['width']=args.width
    models=ROOT/'.cache/local-poc/flashhead-models'
    folder=ROOT/'generated/local-app/audit'
    reference=ROOT/'generated/local-app'/(args.reference+'.png')
    stem=f'flashhead-lite-{args.reference}-{args.width}x{args.height}-s{args.steps}'
    if args.audio!='greeting':stem+='-'+args.audio
    target=folder/(stem+'.mp4')
    started=time.perf_counter()
    pipeline=inference.get_pipeline(1,str(models/'flashhead'),'lite',str(models/'wav2vec2'))
    inference.infer_params['sample_steps']=args.steps
    inference.get_base_data(pipeline,str(reference),42,False)
    torch.cuda.synchronize()
    load_s=time.perf_counter()-started
    params=inference.get_infer_params()
    rate=params['sample_rate'];fps=params['tgt_fps'];motion=params['motion_frames_num']
    count=params['frame_num']-motion
    chunk_samples=count*rate//fps
    audio_source=folder/{'greeting':'listening-timing.wav',
        'cloud-aura1-normal':'cloud-compare-aura-1-normal.wav','kokoro-long':'cloud-compare-kokoro-long.wav'}[args.audio]
    audio,audio_rate=sf.read(audio_source,dtype='float32')
    if audio.ndim!=1:
        raise ValueError('Use the synthetic mono listening-timing WAV.')
    if audio_rate!=rate:
        factor=math.gcd(audio_rate,rate)
        audio=resample_poly(audio,rate//factor,audio_rate//factor)
    samples=args.chunks*chunk_samples
    if len(audio)>samples:
        raise ValueError('Increase chunks to preserve the complete synthetic utterance.')
    audio=np.pad(audio,(0,max(0,samples-len(audio))))[:samples]
    audio_path=folder/(stem+'.wav');sf.write(audio_path,audio,rate,subtype='PCM_16')
    command=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{args.width}x{args.height}',
        '-r',str(fps),'-i','pipe:0','-i',str(audio_path),'-c:v','libx264','-threads','2','-preset','ultrafast',
        '-tune','zerolatency','-crf','18','-pix_fmt','yuv420p','-g','5','-bf','0','-c:a','aac','-shortest',
        '-movflags','+frag_keyframe+empty_moov+default_base_moof',str(target)]
    encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    history=deque([0.]*(rate*params['cached_audio_duration']),maxlen=rate*params['cached_audio_duration'])
    end=params['cached_audio_duration']*fps;begin=end-params['frame_num']
    rows=[];began=time.perf_counter()
    try:
        for index in range(args.chunks):
            t=time.perf_counter()
            history.extend(audio[index*chunk_samples:(index+1)*chunk_samples].tolist())
            features=inference.get_audio_embedding(pipeline,np.asarray(history,dtype=np.float32),begin,end)
            torch.cuda.synchronize();features_s=time.perf_counter()-t
            video=inference.run_pipeline(pipeline,features)[motion:]
            torch.cuda.synchronize();generated_s=time.perf_counter()-t
            frames=video.cpu().numpy().astype(np.uint8)
            if frames.shape!=(count,args.height,args.width,3):
                raise RuntimeError('Unexpected generated frame shape.')
            encoder.stdin.write(frames.tobytes());encoder.stdin.flush()
            row={'index':index,'audio_features_s':round(features_s,3),'generation_s':round(generated_s,3),
                'delivered_s':round(time.perf_counter()-t,3),'frames':count,'output_seconds':count/fps}
            rows.append(row);print(json.dumps(row),flush=True)
        encoder.stdin.close();encoder.wait(timeout=30)
        if encoder.returncode:
            raise RuntimeError('Video encoder failed.')
    finally:
        if encoder.poll() is None:
            encoder.kill();encoder.wait(timeout=10)
        if encoder.stderr:encoder.stderr.close()
    result={'model':'SoulX-FlashHead-1_3B/Model_Lite','code_revision':REVISION,
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'settings':vars(args),
        'synthetic_audio_sha256':hashlib.sha256(audio_source.read_bytes()).hexdigest(),
        'load_and_reference_s':round(load_s,3),'chunks':rows,'generate_and_encode_s':round(time.perf_counter()-began,3),
        'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,
        'torch_peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20,
        'attention':'upstream SDPA fallback; compile disabled','requires_output_review':True,
        'scope':'Synthetic complete WAV, streaming model chunks. Excludes LLM, ASR, speech generation, network and browser.',
        'runtime_selected':False,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (folder/(stem+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
