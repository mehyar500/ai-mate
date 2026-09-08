"""Native ComfyUI joint audio/video benchmark, separate from the live renderer.

Uses the distilled first stage of Comfy-Org's LTX-2.3 workflow. No prompt
enhancer, text-encoder LoRA, custom nodes, or automatic promotion into the app.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
COMFY=ROOT/'.cache/local-poc/ComfyUI'
CHECKPOINT='ltx-2.3-22b-distilled-fp8.safetensors'
ENCODER='gemma_3_12B_it_fp4_mixed.safetensors'
BASE='http://127.0.0.1:8188'


def request(path,body=None):
    data=None if body is None else json.dumps(body).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json'}),timeout=15) as response:
            raw=response.read();return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode('utf-8')[:4000]) from error


def workflow(reference, width=384, height=576, frames=73, seed=50, device='cpu', action='wave'):
    movement={'wave':'She raises her right hand, waves hello once, then lowers it to her side.',
              'closer':'She walks two small steps toward the fixed camera, becoming larger in the frame.',
              'farther':'She walks two small steps backward away from the fixed camera, becoming smaller in the frame.'}[action]
    prompt=('A realistic video of the adult woman in the reference image, standing in the same garden. '
            'The camera remains stationary, with no zoom, pan or cut. Her entire body and both shoes remain visible. '
            +movement+' She looks at the camera and says in a clear, natural female voice, "Hi there, I am Mira." '
            'Her lips and facial expression match her spoken words. The plants and paving stay in place. '
            'Natural overcast daylight, detailed skin, consistent face, clothing and hairstyle. '
            'The audio contains her voice and very faint garden ambience, with no music. No titles or subtitles.')
    node=lambda kind,**inputs:dict(class_type=kind,inputs=inputs)
    return {
        '1':node('CheckpointLoaderSimple',ckpt_name=CHECKPOINT),
        '2':node('LTXAVTextEncoderLoader',text_encoder=ENCODER,ckpt_name=CHECKPOINT,device=device),
        '3':node('CLIPTextEncode',clip=['2',0],text=prompt),
        '4':node('CLIPTextEncode',clip=['2',0],text=''),
        '5':node('LTXVConditioning',positive=['3',0],negative=['4',0],frame_rate=24),
        '6':node('LoadImage',image=reference),
        '7':node('LTXVPreprocess',image=['6',0],img_compression=18),
        '8':node('LTXVImgToVideo',positive=['5',0],negative=['5',1],vae=['1',2],image=['7',0],
                 width=width,height=height,length=frames,batch_size=1,strength=1.0),
        '9':node('LTXVAudioVAELoader',ckpt_name=CHECKPOINT),
        '10':node('LTXVEmptyLatentAudio',frames_number=frames,frame_rate=24,batch_size=1,audio_vae=['9',0]),
        '11':node('LTXVConcatAVLatent',video_latent=['8',2],audio_latent=['10',0]),
        '12':node('RandomNoise',noise_seed=seed),
        '13':node('CFGGuider',model=['1',0],positive=['8',0],negative=['8',1],cfg=1.0),
        '14':node('KSamplerSelect',sampler_name='euler'),
        '15':node('ManualSigmas',sigmas='1.0,0.99375,0.9875,0.98125,0.975,0.909375,0.725,0.421875,0.0'),
        '16':node('SamplerCustomAdvanced',noise=['12',0],guider=['13',0],sampler=['14',0],sigmas=['15',0],latent_image=['11',0]),
        '17':node('LTXVSeparateAVLatent',av_latent=['16',1]),
        '18':node('VAEDecodeTiled',samples=['17',0],vae=['1',2],tile_size=256,overlap=64,temporal_size=32,temporal_overlap=8),
        '19':node('LTXVAudioVAEDecode',samples=['17',1],audio_vae=['9',0]),
        '20':node('CreateVideo',images=['18',0],fps=24,audio=['19',0]),
        '21':node('SaveVideo',video=['20',0],filename_prefix='motion/ltx23',format='mp4',**{'format.codec':'h264'}),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=384);parser.add_argument('--height',type=int,default=576)
    parser.add_argument('--frames',type=int,default=73);parser.add_argument('--seed',type=int,default=50)
    parser.add_argument('--device',choices=['cpu','default'],default='cpu')
    parser.add_argument('--action',choices=['wave','closer','farther'],default='wave')
    parser.add_argument('--timeout',type=int,default=900)
    args=parser.parse_args()
    if any(n<128 or n%32 for n in (args.width,args.height)) or not 9<=args.frames<=241 or args.frames%8!=1:
        parser.error('Dimensions must be multiples of 32; 9..241 frames must be 8n+1.')
    for folder,name in [('checkpoints',CHECKPOINT),('text_encoders',ENCODER)]:
        if not (COMFY/'models'/folder/name).is_file():raise SystemExit('Finish the pinned LTX-2.3 download first.')
    state=request('/queue')
    if state.get('queue_running') or state.get('queue_pending'):raise SystemExit('Wait for an idle motion engine.')
    original=ROOT/'generated/local-app/fullbody.png'
    tag='ltx23-'+uuid.uuid4().hex
    source=COMFY/'input'/(tag+'.png');shutil.copyfile(original,source)
    graph=workflow(source.name,args.width,args.height,args.frames,args.seed,args.device,args.action)
    graph['21']['inputs']['filename_prefix']='motion/'+tag
    audit=ROOT/'generated/local-app/audit';audit.mkdir(exist_ok=True)
    evidence={'model':CHECKPOINT,'encoder':ENCODER,'settings':vars(args),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
              'workflow_source':'https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_ltx2_3_i2v.json',
              'graph':graph,'promoted_to_demo':False}
    destination=audit/(tag+'.json');destination.write_text(json.dumps(evidence,indent=2)+'\n')
    key=None;started=time.perf_counter()
    try:
        key=request('/prompt',{'prompt':graph})['prompt_id'];evidence['prompt_id']=key
        destination.write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps({'prompt_id':key,'evidence':str(destination),'status':'running'}),flush=True)
        deadline=time.monotonic()+args.timeout;next_report=time.monotonic()+30
        while time.monotonic()<deadline:
            history=request('/history/'+key)
            if key in history:
                evidence['history']=history[key];evidence['total_s']=round(time.perf_counter()-started,3)
                evidence['status']='done' if history[key]['status'].get('status_str')=='success' else 'failed'
                destination.write_text(json.dumps(evidence,indent=2)+'\n')
                print(json.dumps({'status':evidence['status'],'total_s':evidence['total_s'],
                                  'outputs':history[key].get('outputs'),'evidence':str(destination)}),flush=True)
                if evidence['status']!='done':raise RuntimeError('Inference failed; see the local benchmark evidence.')
                return
            if time.monotonic()>=next_report:
                print(json.dumps({'prompt_id':key,'elapsed_s':round(time.perf_counter()-started,1),'status':'waiting_for_inference'}),flush=True)
                next_report=time.monotonic()+30
            time.sleep(.5)
        raise TimeoutError('Benchmark exceeded the configured inference limit.')
    except BaseException:
        if key:
            request('/queue',{'delete':[key]});request('/interrupt',{'prompt_id':key})
        raise
    finally:
        source.unlink(missing_ok=True)


if __name__=='__main__':main()
