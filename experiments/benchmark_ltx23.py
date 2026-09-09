"""Native ComfyUI joint audio/video benchmark, separate from the live renderer.

Uses the distilled first stage of Comfy-Org's LTX-2.3 workflow. No prompt
enhancer, text-encoder LoRA, custom nodes, or automatic promotion into the app.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
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


def workflow(reference, width=384, height=576, frames=73, seed=50, device='cpu', action='wave', return_to_reference=False, silent=False, framing='fullbody', idle_style='original', temporal_size=128, compare_decode=False, end_reference=None):
    if return_to_reference and end_reference:
        raise ValueError('Choose either the starting pose or a separate endpoint guide.')
    movement={'wave':'She raises her right hand, waves hello once, then lowers it to her side.',
              'closer':'She walks two small steps straight toward the stationary camera, then stops close to it. Her face and upper body become substantially larger. Her lower legs naturally leave the bottom of the frame as she approaches. She finishes in a relaxed waist-up view, facing the camera.',
              'farther':'She walks two small steps backward away from the fixed camera, becoming smaller in the frame.',
              'idle':'She stands comfortably in the same place throughout, facing the camera. Her feet stay planted and her arms rest beside her hips. She breathes gently, blinks and briefly softens her smile. A soft breeze moves loose strands of hair and the leaves behind her.'}[action]
    speech = (' Her lips stay softly closed. The audio is quiet garden ambience.' if action == 'idle' or silent else
              ' She looks at the camera and says in a clear, natural female voice, "Hi there, I am Mira." '
              'Her lips and facial expression match her spoken words. The audio contains her voice and very faint garden ambience, with no music.')
    prompt=('A realistic video of the adult woman in the reference image, standing in the same garden. '
            'The camera remains stationary, with no zoom, pan or cut. '
            +movement+speech+' The paving and garden layout stay in place. '
            'Natural overcast daylight, detailed skin, consistent face, clothing and hairstyle.')
    if action=='closer' and end_reference:
        prompt=('A continuous photographic video of the adult woman walking gently toward a fixed camera in the same garden. '
                'She takes one small step, slows down, and stops at the position in the final reference image. '
                'Her entire head and hair remain visible with clear space above them throughout. '
                'She remains still for the final second, arms relaxed, both eyes open and lips softly closed. '
                'The camera never moves or zooms. Consistent identity, anatomy, sweater, jeans and garden. '
                'Natural walking speed and soft daylight. Quiet garden ambience.')
    if action=='idle' and framing=='close':
        prompt=('A photographic close-up portrait video of the adult woman in the reference image. '
                'She stays at exactly the same distance from the fixed camera, with her head the same size in the frame. '
                'The only visible movement is one natural blink: her eyelids close fully and open again. '
                'Her chin, nose, shoulders and relaxed closed lips stay in the same positions. '
                'A light breeze moves fine strands of her hair. The garden remains in the same '
                'position. Detailed natural skin, soft daylight, continuous steady close-up, quiet garden ambience.')
    if action=='idle' and idle_style=='calm':
        view = ('Her full body and both shoes remain in exactly the same place in the frame. '
                if framing=='fullbody' else 'Her face stays exactly the same size and position in the close view. ')
        prompt=('A quiet photographic video of the adult woman in the reference image listening to a friend. '
                'The camera is completely fixed. '+view+
                'She maintains attentive eye contact with both eyes open throughout, except for one '
                'split-second reflex blink lasting just one fifth of a second. The left and right eyelids '
                'close and reopen simultaneously. Her gaze immediately returns to the camera. '
                'Her lips rest closed and her head stays level. '
                'Only very subtle breathing moves her shoulders. Her hair rests naturally against her sweater. '
                'It is a completely windless day in a sheltered garden. All leaves, twigs and branches '
                'remain stationary throughout the shot. Natural real-time speed, quiet garden ambience, steady soft daylight.')
    node=lambda kind,**inputs:dict(class_type=kind,inputs=inputs)
    graph = {
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
        '18':node('VAEDecodeTiled',samples=['17',0],vae=['1',2],tile_size=256,overlap=64,temporal_size=temporal_size,temporal_overlap=8),
        '19':node('LTXVAudioVAEDecode',samples=['17',1],audio_vae=['9',0]),
        '20':node('CreateVideo',images=['18',0],fps=24,audio=['19',0]),
        '21':node('SaveVideo',video=['20',0],filename_prefix='motion/ltx23',format='mp4',**{'format.codec':'h264'}),
    }
    if return_to_reference or end_reference:
        guide_image=['7',0]
        if end_reference:
            graph['27']=node('LoadImage',image=end_reference)
            graph['28']=node('LTXVPreprocess',image=['27',0],img_compression=18)
            guide_image=['28',0]
        graph['22']=node('LTXVAddGuide',positive=['8',0],negative=['8',1],latent=['8',2],
                         vae=['1',2],image=guide_image,frame_idx=-1,strength=1.0)
        graph['11']['inputs']['video_latent']=['22',2]
        graph['13']['inputs'].update(positive=['22',0],negative=['22',1])
        graph['23']=node('LTXVCropGuides',positive=['22',0],negative=['22',1],latent=['17',0])
        graph['18']['inputs']['samples']=['23',2]
    if compare_decode:
        # Decode exactly the same sampled video twice. This isolates temporal
        # tiling from prompt/seed/model changes when reviewing double images.
        graph['24']=node('VAEDecodeTiled',**dict(graph['18']['inputs'],temporal_size=32))
        graph['25']=node('CreateVideo',images=['24',0],fps=24,audio=['19',0])
        graph['26']=node('SaveVideo',video=['25',0],filename_prefix='motion/ltx23-temporal32',format='mp4',**{'format.codec':'h264'})
    return graph


def reviewed_reference_path(path):
    original=path.resolve()
    candidate_reference = (original.parent.parent == (ROOT/'generated/local-app/audit').resolve()
                           and re.fullmatch(r'performance-[a-z0-9-]{1,32}', original.parent.name)
                           and original.name == 'performance-near.png')
    if (original.parent != (ROOT/'generated/local-app').resolve() and not candidate_reference) or original.suffix != '.png' or not original.is_file():
        raise ValueError('The reference must be an existing reviewed app-owned PNG.')
    return original


def main():
    global BASE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=384);parser.add_argument('--height',type=int,default=576)
    parser.add_argument('--frames',type=int,default=73);parser.add_argument('--seed',type=int,default=50)
    parser.add_argument('--device',choices=['cpu','default'],default='cpu')
    parser.add_argument('--action',choices=['wave','closer','farther','idle'],default='wave')
    endpoint=parser.add_mutually_exclusive_group()
    endpoint.add_argument('--return-to-reference',action='store_true',help='Add end-pose guidance before combining audio/video latents.')
    endpoint.add_argument('--end-reference-path',type=Path,help='Reviewed app-owned final pose; benchmark only, never automatically promoted.')
    parser.add_argument('--silent',action='store_true',help='Generate movement with quiet ambience; app speech is added separately.')
    parser.add_argument('--reference-path',type=Path,help='Reviewed app-owned PNG; defaults to the full-body reference.')
    parser.add_argument('--framing',choices=['fullbody','close'],default='fullbody')
    parser.add_argument('--idle-style',choices=['original','calm'],default='original')
    parser.add_argument('--temporal-size',type=int,choices=[32,64,128,256],default=128,help='Video VAE decode window in output frames; 128 avoids internal time seams in the measured 97-frame clips.')
    parser.add_argument('--compare-decode',action='store_true',help='Also decode the identical latent with the original 32-frame window.')
    parser.add_argument('--timeout',type=int,default=900)
    parser.add_argument('--worker-port',type=int,default=8188,help='Loopback worker port; run this benchmark on the GPU host.')
    parser.add_argument('--hourly-cost',type=float,default=0,help='Actual instance hourly rate; estimate excludes storage and unrelated idle time.')
    args=parser.parse_args()
    if not 1024 <= args.worker_port <= 65535:
        parser.error('Worker port must be between 1024 and 65535.')
    if not math.isfinite(args.hourly_cost) or args.hourly_cost < 0:
        parser.error('Hourly cost must be a finite non-negative number.')
    BASE=f'http://127.0.0.1:{args.worker_port}'
    if any(n<128 or n%32 for n in (args.width,args.height)) or not 9<=args.frames<=241 or args.frames%8!=1:
        parser.error('Dimensions must be multiples of 32; 9..241 frames must be 8n+1.')
    for folder,name in [('checkpoints',CHECKPOINT),('text_encoders',ENCODER)]:
        if not (COMFY/'models'/folder/name).is_file():raise SystemExit('Finish the pinned LTX-2.3 download first.')
    hardware=request('/system_stats')
    state=request('/queue')
    if state.get('queue_running') or state.get('queue_pending'):raise SystemExit('Wait for an idle motion engine.')
    try:
        original=reviewed_reference_path(args.reference_path or ROOT/'generated/local-app/fullbody.png')
        end_original=reviewed_reference_path(args.end_reference_path) if args.end_reference_path else None
    except ValueError as error:
        parser.error(str(error))
    tag='ltx23-'+uuid.uuid4().hex
    source=COMFY/'input'/(tag+'.png');shutil.copyfile(original,source)
    end_source=COMFY/'input'/(tag+'-end.png') if end_original else None
    if end_source:
        shutil.copyfile(end_original,end_source)
    graph=workflow(source.name,args.width,args.height,args.frames,args.seed,args.device,args.action,args.return_to_reference,args.silent,args.framing,args.idle_style,args.temporal_size,args.compare_decode,
                   end_reference=end_source.name if end_source else None)
    graph['21']['inputs']['filename_prefix']='motion/'+tag
    if args.compare_decode:
        graph['26']['inputs']['filename_prefix']='motion/'+tag+'-temporal32'
    audit=ROOT/'generated/local-app/audit';audit.mkdir(exist_ok=True)
    evidence={'model':CHECKPOINT,'encoder':ENCODER,'settings':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
              'workflow_source':'https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_ltx2_3_i2v.json',
              'graph':graph,'promoted_to_demo':False,
              'worker_devices':hardware.get('devices',[]),
              'rental_cost_scope':'Elapsed submitted job only; excludes installation, prewarming, storage, idle time and transfer.'}
    if end_original:
        evidence['end_reference_sha256']=hashlib.sha256(end_original.read_bytes()).hexdigest()
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
                evidence['estimated_job_compute_usd']=round(evidence['total_s']*args.hourly_cost/3600,6) if args.hourly_cost else None
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
        if end_source:
            end_source.unlink(missing_ok=True)


if __name__=='__main__':main()
