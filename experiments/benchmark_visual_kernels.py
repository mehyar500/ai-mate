"""Isolated neural-stage timing with synthetic inputs; no app/model selection."""
import argparse
import json
from pathlib import Path
import re
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.visual import PortraitRenderer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label.')
    folder = ROOT/'generated/local-app/audit'/('visual-kernels-'+args.label)
    folder.mkdir(exist_ok=False)
    renderer = PortraitRenderer()
    torch = renderer.torch
    renderer.prepare('fullbody', reference_path=ROOT/'generated/local-app/performance-near.png')
    with torch.inference_mode():
        latent = renderer.latent.expand(8,-1,-1,-1).clone().contiguous(memory_format=torch.channels_last)
        generator = torch.Generator(device='cuda').manual_seed(731)
        conditions = [torch.randn((8,50,384),device='cuda',dtype=renderer.dtype,generator=generator)*.2+renderer.pe for _ in range(12)]
        timestep = torch.tensor(0,device='cuda')
        for _ in range(3):
            prediction=renderer.unet(latent,timestep,encoder_hidden_states=conditions[0]).sample
            renderer.vae.decode(prediction/renderer.vae.config.scaling_factor).sample
        torch.cuda.synchronize()
        rows=[]
        for index,condition in enumerate(conditions):
            start=time.perf_counter()
            prediction=renderer.unet(latent,timestep,encoder_hidden_states=condition).sample
            torch.cuda.synchronize(); unet_s=time.perf_counter()-start
            start=time.perf_counter()
            decoded=renderer.vae.decode(prediction/renderer.vae.config.scaling_factor).sample
            torch.cuda.synchronize(); vae_s=time.perf_counter()-start
            start=time.perf_counter()
            ((decoded/2+.5).clamp(0,1).permute(0,2,3,1).float().cpu().numpy()*255).round().astype('uint8')
            transfer_s=time.perf_counter()-start
            rows.append(dict(index=index,unet_s=unet_s,vae_s=vae_s,transfer_s=transfer_s))
    result={'torch':torch.__version__,'cuda':torch.version.cuda,'batch':8,'rows':rows,
            'median_s':{key:statistics.median(row[key] for row in rows) for key in ['unet_s','vae_s','transfer_s']},
            'scope':'Warm fixed batch8 synthetic conditioning, reviewed close-reference appearance. Excludes ASR, dialogue, speech, tracking, encoding, browser and perceptual quality.'}
    (folder/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
