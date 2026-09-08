"""Direct Diffusers LTX benchmark using existing weights; no ComfyUI imports/API.

The same quantized checkpoint is cast to BF16. Record this precision difference
when comparing with ComfyUI's FP8 kernels. Config architecture matches the
checkpoint metadata; config-only assets are pinned to the official 0.9.5 layout.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.motion import PROMPTS  # Shared bounded text only; no ComfyUI package or service call.

CACHE=ROOT/'.cache/local-poc'
CHECKPOINT=CACHE/'ComfyUI/models/checkpoints/ltxv-2b-0.9.8-distilled-fp8.safetensors'
ENCODER=CACHE/'ComfyUI/models/text_encoders/t5xxl_fp8_e4m3fn.safetensors'
CONFIG=CACHE/'ltx-diffusers-config'
CONFIG_REVISION='e58e28c39631af4d1468ee57a853764e11c1d37e'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',choices=tuple(PROMPTS),default='wave')
    parser.add_argument('--seed',type=int,default=50)
    parser.add_argument('--width',type=int,default=384);parser.add_argument('--height',type=int,default=576)
    parser.add_argument('--frames',type=int,default=73);parser.add_argument('--runs',type=int,default=2)
    parser.add_argument('--return-to-reference',action='store_true')
    parser.add_argument('--prepare-config',action='store_true',help='Fetch pinned official config/tokenizer files only, not weights.')
    args=parser.parse_args()
    if any(n<128 or n%32 for n in [args.width,args.height]) or not 9<=args.frames<=241 or args.frames%8!=1:
        parser.error('Use dimensions divisible by 32 and 9..241 frames of the form 8n+1.')
    if not 1<=args.runs<=5:parser.error('Use one to five measured runs.')
    if args.prepare_config:
        from huggingface_hub import snapshot_download
        snapshot_download('Lightricks/LTX-Video-0.9.5',revision=CONFIG_REVISION,
                          allow_patterns=['model_index.json','*/config.json','tokenizer/*','scheduler/*'],
                          local_dir=CONFIG,token=False)
    if not (CONFIG/'transformer/config.json').is_file():
        parser.error('Run once with --prepare-config to download the pinned architecture/tokenizer files.')
    import torch
    from accelerate import init_empty_weights
    from safetensors.torch import load_file,save_file
    from transformers import T5Config,T5EncoderModel,T5TokenizerFast
    from diffusers import LTXConditionPipeline,LTXVideoTransformer3DModel,AutoencoderKLLTXVideo,FlowMatchEulerDiscreteScheduler
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
    from PIL import Image
    import numpy as np
    torch.set_num_threads(4)
    dtype=torch.bfloat16
    # Keep capacity for the already-running MuseTalk renderer; fail rather than overcommit it.
    torch.cuda.set_per_process_memory_fraction(.73)
    started=time.perf_counter()
    source=ROOT/'generated/local-app/fullbody.png'
    prompt=PROMPTS[args.action]
    prompt_hash=hashlib.sha256((prompt+CONFIG_REVISION+'seq256-bf16').encode()).hexdigest()
    embeddings=CACHE/('ltx-direct-prompt-'+prompt_hash+'.safetensors')
    encoder_s=0.0
    if not embeddings.exists():
        print('Preparing direct T5 prompt embeddings on GPU.',flush=True)
        began=time.perf_counter()
        config=T5Config.from_pretrained(str(CONFIG/'text_encoder'),local_files_only=True)
        with init_empty_weights():text_encoder=T5EncoderModel(config)
        state={k:v.to(dtype) for k,v in load_file(str(ENCODER)).items()}
        if 'encoder.embed_tokens.weight' not in state:state['encoder.embed_tokens.weight']=state['shared.weight']
        text_encoder.load_state_dict(state,assign=True,strict=True);del state
        text_encoder.to('cuda').eval()
        tokenizer=T5TokenizerFast.from_pretrained(str(CONFIG/'tokenizer'),local_files_only=True)
        tokens=tokenizer(prompt,padding='max_length',max_length=256,truncation=True,return_tensors='pt')
        with torch.inference_mode():hidden=text_encoder(tokens.input_ids.to('cuda'),attention_mask=tokens.attention_mask.to('cuda'))[0]
        save_file({'prompt_embeds':hidden.cpu().contiguous(),'prompt_attention_mask':tokens.attention_mask.bool().contiguous()},str(embeddings))
        del hidden,text_encoder,tokenizer,tokens;gc.collect();torch.cuda.empty_cache()
        encoder_s=time.perf_counter()-began
        print(json.dumps({'prompt_encoder_s':round(encoder_s,3)}),flush=True)
    print('Loading direct LTX transformer and VAE from existing checkpoint.',flush=True)
    transformer=LTXVideoTransformer3DModel.from_single_file(str(CHECKPOINT),config=str(CONFIG),subfolder='transformer',torch_dtype=dtype,local_files_only=True)
    vae=AutoencoderKLLTXVideo.from_single_file(str(CHECKPOINT),config=str(CONFIG),subfolder='vae',torch_dtype=dtype,local_files_only=True)
    vae.enable_tiling(tile_sample_min_height=256,tile_sample_min_width=256,tile_sample_stride_height=224,tile_sample_stride_width=224)
    pipe=LTXConditionPipeline(transformer=transformer,vae=vae,text_encoder=None,tokenizer=None,
                             scheduler=FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000,shift=1,use_dynamic_shifting=False))
    pipe.to('cuda')
    encoded=load_file(str(embeddings),device='cuda')
    reference=Image.open(source).convert('RGB')
    conditions=[LTXVideoCondition(image=reference,frame_index=0,strength=1)]
    if args.return_to_reference:conditions.append(LTXVideoCondition(image=reference,frame_index=args.frames-1,strength=1))
    audit=ROOT/'generated/local-app/audit';audit.mkdir(exist_ok=True)
    evidence={'engine':'diffusers','diffusers_version':__import__('diffusers').__version__,'comfyui_dependency':False,
              'checkpoint':CHECKPOINT.name,'precision':'FP8 checkpoint weights cast to BF16; not FP8 matrix multiplication',
              'config_revision':CONFIG_REVISION,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'settings':vars(args),'prompt_encoder_s':round(encoder_s,3),'setup_s':round(time.perf_counter()-started,3),'runs':[]}
    label=f'direct-ltx-{args.action}-{args.seed}-{args.width}x{args.height}-{args.frames}'
    report=audit/(label+'.json')
    report.write_text(json.dumps(evidence,indent=2)+'\n')
    for run in range(args.runs):
        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();began=time.perf_counter();steps=[]
        def on_step(pipeline,index,timestep,kwargs):
            torch.cuda.synchronize();steps.append(round(time.perf_counter()-began,3));return kwargs
        with torch.inference_mode():
            result=pipe(conditions=conditions,prompt_embeds=encoded['prompt_embeds'],prompt_attention_mask=encoded['prompt_attention_mask'],
                        width=args.width,height=args.height,num_frames=args.frames,frame_rate=24,num_inference_steps=8,
                        timesteps=[1000,993.7,987.5,981.2,975,909.4,725,421.9],guidance_scale=1,
                        image_cond_noise_scale=0,decode_timestep=.05,decode_noise_scale=.025,
                        generator=torch.Generator('cpu').manual_seed(args.seed),callback_on_step_end=on_step).frames[0]
        torch.cuda.synchronize();render_s=time.perf_counter()-began
        destination=audit/f'{label}-{run}.mp4'
        command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                 '-s',f'{args.width}x{args.height}','-r','24','-i','pipe:0','-an','-c:v','libx264',
                 '-preset','ultrafast','-threads','2','-crf','18','-pix_fmt','yuv420p',str(destination)]
        with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as writer:
            for frame in result:writer.stdin.write(np.asarray(frame).tobytes())
            writer.stdin.close();error=writer.stderr.read();status=writer.wait()
            if status:raise RuntimeError('Video encoder failed: '+error.decode('utf-8',errors='replace')[:1000])
        metrics={'run':run,'render_s':round(render_s,3),'total_with_encode_s':round(time.perf_counter()-began,3),
                 'steps_elapsed_s':steps,'frames':len(result),'peak_allocated_mib':round(torch.cuda.max_memory_allocated()/2**20,1),
                 'peak_reserved_mib':round(torch.cuda.max_memory_reserved()/2**20,1),'video':str(destination)}
        evidence['runs'].append(metrics);report.write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(metrics),flush=True)


if __name__=='__main__':main()
