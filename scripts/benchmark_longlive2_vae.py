"""Measure the actual Wan2.2 VAE on repeated reference latents, not body generation."""
import argparse
import gc
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_longlive2 import checksum, install_streaming_vae


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--latent-chunk', type=int, choices=[1, 2, 4, 8], default=8)
    parser.add_argument('--width', type=int, choices=[256, 320, 384], default=320)
    parser.add_argument('--height', type=int, choices=[384, 480, 576], default=480)
    parser.add_argument('--vae', choices=['wan', 'light-v2'], default='wan')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a new lowercase label.')
    with urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=5) as response:
        status = json.load(response)
    if status.get('busy'):
        raise RuntimeError('Preview call active; postpone the GPU probe.')
    manifest = json.loads((ROOT / 'config/longlive2-benchmark.json').read_text(encoding='utf-8'))
    spec = next(row for row in manifest['files'] if row['filename'] == 'Wan2.2_VAE.pth')
    weights = ROOT / '.cache/local-poc/longlive2-models'
    if checksum(weights / spec['folder'] / spec['filename']) != spec['sha256']:
        raise ValueError('VAE checkpoint failed verification.')
    if args.vae == 'light-v2':
        light = next(row for row in manifest['optional_files'] if row['filename'] == 'MG-LightVAE_v2.pth')
        if checksum(weights / light['folder'] / light['filename']) != light['sha256']:
            raise ValueError('Light VAE checkpoint failed verification.')
    sys.path[:0] = [str(ROOT / '.cache/longlive2-deps'), str(ROOT / '.cache/local-poc/LongLive2')]
    import torch
    import numpy as np
    from PIL import Image
    from utils.wan_5b_wrapper import WanVAEWrapper
    os.chdir(weights)
    output = ROOT / 'generated/local-app/audit' / ('longlive2-vae-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'scope': 'synthetic repeated reference latent decoder sizing; no body action or speech',
              'settings': vars(args), 'preview_loaded_but_idle': True, 'complete': False, 'chunks': []}
    try:
        torch.set_num_threads(8)
        torch.set_grad_enabled(False)
        vae = WanVAEWrapper().eval().requires_grad_(False).to('cuda', dtype=torch.bfloat16)
        image = Image.open(ROOT / 'generated/local-app/fullbody.png').convert('RGB').resize(
            (args.width, args.height), Image.Resampling.LANCZOS)
        pixels = torch.from_numpy(np.asarray(image).copy()).permute(2, 0, 1)[None, :, None].to('cuda', dtype=torch.bfloat16) / 127.5 - 1
        with torch.autocast('cuda', dtype=torch.bfloat16):
            latent = vae.encode_to_latent(pixels).to(torch.bfloat16)
        if args.vae == 'light-v2':
            del vae
            gc.collect()
            torch.cuda.empty_cache()
            from utils.lightvae_5b_wrapper import LightVAE5BWrapper
            vae = LightVAE5BWrapper(str(weights / light['folder'] / light['filename']))
            record['pruning_rate'] = vae.pruning_rate
        with torch.autocast('cuda', dtype=torch.bfloat16):
            control = vae.decode_to_pixel(latent.repeat(1, 4, 1, 1, 1))
        if args.vae == 'wan':
            install_streaming_vae(vae.model)
        vae.model.clear_cache()
        with torch.autocast('cuda', dtype=torch.bfloat16):
            first = vae.decode_to_pixel(latent.repeat(1, 2, 1, 1, 1), use_cache=True)
            second = vae.decode_to_pixel(latent.repeat(1, 2, 1, 1, 1), use_cache=True)
            joined = torch.cat([first, second], dim=1)
        record['streaming_control'] = {'frames': joined.shape[1],
                                       'max_absolute_error': float((control - joined).abs().max())}
        reconstruction = ((control[0, 0].permute(1, 2, 0).cpu().numpy() + 1) * 127.5).round().clip(0, 255).astype('uint8')
        Image.fromarray(reconstruction).save(output / 'reconstruction.png')
        torch.testing.assert_close(control, joined, atol=0.016, rtol=0)
        del control, first, second, joined
        vae.model.clear_cache()
        expanded = latent.repeat(1, args.latent_chunk, 1, 1, 1)
        for index in range(3):
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            began = time.perf_counter()
            with torch.autocast('cuda', dtype=torch.bfloat16):
                decoded = vae.decode_to_pixel(expanded, use_cache=True)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - began
            row = {'index': index, 'seconds': elapsed, 'frames': decoded.shape[1],
                   'fps': decoded.shape[1] / elapsed, 'peak_allocated_mib': torch.cuda.max_memory_allocated() / 2**20}
            record['chunks'].append(row)
            print(json.dumps(row), flush=True)
            del decoded
        record['complete'] = True
    except Exception as error:
        record.update({'error_type': type(error).__name__, 'error': str(error)[:1000]})
        raise
    finally:
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
