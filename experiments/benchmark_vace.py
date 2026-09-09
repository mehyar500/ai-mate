"""Isolated, fully clothed VACE reference-and-pose quality test on the local GPU.

Uses original Apache-2.0 Wan inference. This is an offline clip-quality test,
not a streaming implementation. No live app, private history or credentials.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / '.cache/local-poc/Wan2.1'
WEIGHTS = ROOT / '.cache/local-poc/vace-models/Wan2.1-VACE-1.3B'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preflight(manifest, prepare_only, rcm=False, tiny=False):
    revision = subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != manifest['wan_code']['revision'] or subprocess.check_output(['git', '-C', str(CODE), 'diff', '--no-ext-diff']):
        raise ValueError('Expected the clean, pinned Wan checkout.')
    from experiments.benchmark_rain import preflight as pose_preflight
    pose_preflight(json.loads((ROOT / 'config/rain-benchmark.json').read_text()), prepare_only=True)
    if not prepare_only:
        rows = manifest['files'] + manifest['reused_files']
        if rcm:
            rows += manifest['rcm_experiment']['files']
        if tiny:
            rows += manifest['tiny_vae_experiment']['files']
        for row in rows:
            path = ROOT / row['path'] if 'path' in row else WEIGHTS.parent / row['folder'] / row['filename']
            if not path.is_file() or path.stat().st_size != row['size'] or checksum(path) != row['sha256']:
                raise ValueError('Missing or unverified VACE asset: ' + path.name)


def dense_attention(q, k, v, q_lens=None, k_lens=None, **kwargs):
    """The single-video test has no padded tokens; reject truncated lengths."""
    if q_lens is not None and not bool((q_lens == q.shape[1]).all()):
        raise ValueError('Padded query sequences are outside this test.')
    if k_lens is not None and not bool((k_lens == k.shape[1]).all()):
        raise ValueError('Padded key sequences are outside this test.')
    from experiments.benchmark_longlive2 import sdpa_attention
    return sdpa_attention(q, k, v, **kwargs)


def run(args, record, output, manifest):
    sys.path[:0] = [str(ROOT / '.cache/longlive2-deps'), str(CODE),
                   str(ROOT / '.cache/local-poc/RAIN'), str(ROOT)]
    # Reuse pose drawing's optional matplotlib dependency without overriding
    # the app's newer diffusers/transformers with RAIN's older versions.
    pose_dependencies = str(ROOT / '.cache/rain-deps')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    import torch
    from safetensors.torch import load_file, save_file
    from experiments.benchmark_rain import controls

    torch.set_num_threads(8)
    torch.set_grad_enabled(False)
    sys.path.append(pose_dependencies)
    try:
        reference, control_images = controls(args, output, record)
    finally:
        sys.path.remove(pose_dependencies)
    control_rgb = np.stack([np.asarray(im) for im in control_images])
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                    '-video_size', f'{args.width}x{args.height}', '-framerate', '16', '-i', 'pipe:0',
                    '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                    str(output / 'controls.mp4')], input=control_rgb.tobytes(), check=True, timeout=60)
    if args.prepare_only:
        record['controls_only'] = True
        record['complete'] = True
        return

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required.')
    free, total = torch.cuda.mem_get_info()
    record['gpu'] = {'name': torch.cuda.get_device_name(), 'free_bytes_before': free, 'total_bytes': total}
    if free < 14_000_000_000:
        raise RuntimeError('Exclusive benchmark requires 14GB free; pause only the verified idle preview.')
    from wan.vace import WanVace
    from wan.modules.vace_model import VaceWanModel
    from wan.modules.t5 import umt5_xxl
    from wan.modules.tokenizers import HuggingfaceTokenizer
    from wan.modules.vae import WanVAE
    import wan.modules.model as model_module
    model_module.flash_attention = dense_attention
    dtype, device = torch.bfloat16, torch.device('cuda')
    prompt = ('A realistic full body video of the same adult woman in the reference photograph, '
              'wearing the same cream sweater, blue jeans and white shoes in the same garden. '
              f'She slowly raises her {args.side} hand to shoulder height, holds it up, then lowers it. '
              'Her other arm stays down. Fixed camera. Her entire body and feet remain visible.')
    if args.motion == 'static':
        prompt = ('A realistic full body video of the same adult woman in the reference photograph, '
                  'wearing the same cream sweater, blue jeans and white shoes in the same garden. '
                  'She stands calmly with both arms down. Fixed camera. Her whole body and feet are visible.')
    negative = 'blurred face, distorted anatomy, extra limbs, detached hands, changing clothes, cuts, camera zoom, text'
    record['prompt'], record['negative_prompt'] = prompt, negative
    reused = {row['filename']: ROOT / row['path'] for row in manifest['reused_files']}
    cache = WEIGHTS / ('text-' + hashlib.sha256(json.dumps([prompt, negative]).encode()).hexdigest()[:20] + '.safetensors')
    started = time.perf_counter()
    if cache.is_file():
        encoded = load_file(str(cache))
        record['prompt_cache_hit'] = True
    else:
        with torch.device('meta'):
            encoder = umt5_xxl(encoder_only=True, return_tokenizer=False, dtype=dtype, device='meta')
        state = torch.load(reused['models_t5_umt5-xxl-enc-bf16.pth'], weights_only=True, mmap=True, map_location='cpu')
        encoder.load_state_dict(state, assign=True, strict=True)
        del state
        encoder.eval().requires_grad_(False).to(device=device, dtype=dtype)
        tokenizer = HuggingfaceTokenizer(str(reused['google/umt5-xxl/tokenizer.json'].parent),
                                        seq_len=512, clean='whitespace', local_files_only=True)
        encoded = {}
        for i, text in enumerate([prompt, negative]):
            ids, mask = tokenizer([text], return_mask=True, add_special_tokens=True)
            context = encoder(ids.to(device), mask.to(device))
            encoded[str(i)] = context[0, :int(mask.sum())].cpu().contiguous()
        save_file(encoded, str(cache))
        del encoder, tokenizer, context, ids, mask
        gc.collect()
        torch.cuda.empty_cache()
        record['prompt_cache_hit'] = False
    record['prompt_preparation_s'] = time.perf_counter() - started
    print(json.dumps({'prompt_preparation_s': record['prompt_preparation_s']}), flush=True)

    class CachedText:
        def __call__(self, texts, target):
            return [encoded[str([prompt, negative].index(text))].to(target) for text in texts]

    # Populate the original inference object's components without loading a
    # second 11GB text encoder or FP32 GPU copy of the diffusion model.
    pipe = object.__new__(WanVace)
    pipe.device, pipe.rank, pipe.sp_size = device, 0, 1
    pipe.param_dtype, pipe.num_train_timesteps = dtype, 1000
    pipe.t5_cpu, pipe.text_encoder = True, CachedText()
    pipe.sample_neg_prompt = negative
    pipe.vae_stride, pipe.patch_size = (4, 8, 8), (1, 2, 2)
    started = time.perf_counter()
    config = json.loads((WEIGHTS / 'config.json').read_text())
    with torch.device('meta'):
        model = VaceWanModel.from_config(config)
    state = load_file(str(WEIGHTS / 'diffusion_pytorch_model.safetensors'))
    if args.generator == 'rcm':
        from scripts.vace_rcm import transfer_generator
        accelerated = torch.load(WEIGHTS.parent / 'rcm-Wan/rCM_Wan2.1_T2V_1.3B_480p.pt',
                                 weights_only=True, mmap=True, map_location='cpu')
        state, record['rcm_transfer'] = transfer_generator(state, accelerated)
        del accelerated
    model.load_state_dict(state, assign=True, strict=True)
    del state
    d = model.dim // model.num_heads
    model.freqs = torch.cat([model_module.rope_params(1024, d - 4 * (d // 6)),
                            model_module.rope_params(1024, 2 * (d // 6)),
                            model_module.rope_params(1024, 2 * (d // 6))], dim=1)
    pipe.model = model.eval().requires_grad_(False).to(device=device, dtype=dtype)
    if args.vae == 'tiny-both':
        from scripts.vace_tiny_vae import TinyWanVAE
        pipe.vae = TinyWanVAE(device=device)
    else:
        pipe.vae = WanVAE(vae_pth=str(reused['Wan2.1_VAE.pth']), dtype=dtype, device=device)
        pipe.vae.model.to(dtype=dtype)
        if args.vae == 'tiny-decode':
            from scripts.vace_tiny_vae import TinyWanVAE
            tiny = TinyWanVAE(device=device)
            pipe.vae.decode = tiny.decode
    torch.cuda.synchronize()
    record['model_load_s'] = time.perf_counter() - started
    print(json.dumps({'model_load_s': record['model_load_s']}), flush=True)

    frames = torch.from_numpy(control_rgb.copy()).permute(3, 0, 1, 2).to(device=device, dtype=dtype) / 127.5 - 1
    ref = torch.from_numpy(np.asarray(reference).copy()).permute(2, 0, 1)[:, None].to(device=device, dtype=dtype) / 127.5 - 1
    mask = torch.ones((1, args.frames, args.height, args.width), device=device, dtype=dtype)
    if args.conditioning in ('masked-body', 'masked-body-open-canvas'):
        # VACE sees original pixels outside the union of commanded body poses.
        # This is an inpainting condition, not post-render background compositing.
        from scripts.vace_rcm import body_control_bounds
        pose = np.load(output / 'controls.npz', allow_pickle=False)
        left, top, right, bottom = body_control_bounds(pose['points'], pose['scores'], (args.width, args.height))
        mask.zero_()
        mask[:, :, top:bottom, left:right] = 1
        padding_count = 0
        if args.conditioning == 'masked-body-open-canvas':
            # ImageOps.pad introduced all-black columns. Keep them editable so
            # a raised hand can occupy the wider output instead of being cut off.
            padding = np.all(np.asarray(reference) == 0, axis=(0, 2))
            mask[:, :, :, torch.from_numpy(padding).to(device)] = 1
            padding_count = int(padding.sum())
        frames = frames * mask + ref.expand(-1, args.frames, -1, -1) * (1 - mask)
        record['conditioning'] = {'type': args.conditioning, 'editable_xyxy': [left, top, right, bottom],
                                   'editable_padding_columns': padding_count,
                                   'post_render_compositing': False}
    torch.cuda.reset_peak_memory_stats()
    began = time.perf_counter()
    if args.generator == 'rcm':
        from scripts.vace_rcm import sample
        video = sample(pipe, prompt, frames, mask, ref, args, record)
    else:
        video = pipe.generate(prompt, [frames], [mask], [[ref]], size=(args.width, args.height), frame_num=args.frames,
                              context_scale=args.context_scale, sampling_steps=args.steps, guide_scale=5., shift=16.,
                              seed=args.seed, offload_model=False, n_prompt=negative)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - began
    if args.generator == 'rcm':
        save_file({'latents': pipe._benchmark_latents.detach().cpu().contiguous()}, str(output / 'latents.safetensors'))
    if tuple(video.shape) != (3, args.frames, args.height, args.width) or not torch.isfinite(video).all():
        raise ValueError('Invalid generated frame dimensions or nonfinite pixels.')
    rgb = ((video.permute(1, 2, 3, 0).cpu().float().clamp(-1, 1).numpy() + 1) * 127.5).round().astype(np.uint8)
    path = output / 'run-0.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                    '-video_size', f'{args.width}x{args.height}', '-framerate', '16', '-i', 'pipe:0',
                    '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(path)],
                   input=rgb.tobytes(), check=True, timeout=60)
    record['run'] = {'inference_s': elapsed, 'generated_frames': len(rgb), 'generated_fps': len(rgb) / elapsed,
                     'first_decoded_output_s': elapsed, 'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                     'peak_reserved_bytes': torch.cuda.max_memory_reserved(), 'sha256': checksum(path)}
    if args.decoder_comparison:
        from scripts.vace_tiny_vae import TinyWanVAE
        tiny = TinyWanVAE(device=device)
        began = time.perf_counter()
        compared = tiny.decode([pipe._benchmark_latents[:, 1:]])[0]
        torch.cuda.synchronize()
        decode_s = time.perf_counter() - began
        if compared.shape != video.shape or not torch.isfinite(compared).all():
            raise ValueError('Tiny decoder produced invalid frame dimensions/pixels.')
        comparison_rgb = ((compared.permute(1, 2, 3, 0).cpu().float().clamp(-1, 1).numpy() + 1) * 127.5).round().astype(np.uint8)
        comparison_path = output / 'tiny-decoded.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                        '-video_size', f'{args.width}x{args.height}', '-framerate', '16', '-i', 'pipe:0',
                        '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(comparison_path)],
                       input=comparison_rgb.tobytes(), check=True, timeout=60)
        record['decoder_comparison'] = {'same_generated_latents': True, 'tiny_decode_s': decode_s,
                                        'pixel_mae_0_1': float((compared - video).abs().mean() / 2),
                                        'sha256': checksum(comparison_path), 'scope': 'Decoder only; excludes model loading'}
    record['complete'] = True
    print(json.dumps(record['run']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--side', choices=['right', 'left'], default='right')
    parser.add_argument('--motion', choices=['raise-lower', 'static'], default='raise-lower')
    parser.add_argument('--size', type=int, choices=[384, 512], default=512)
    parser.add_argument('--aspect', choices=['square', 'portrait'], default='square')
    parser.add_argument('--pose-profile', choices=['wide', 'compact'], default='wide')
    parser.add_argument('--frames', type=int, choices=[17, 33, 49], default=33)
    parser.add_argument('--trajectory-frames', type=int, choices=[17, 33, 49], default=None)
    parser.add_argument('--frame-offset', type=int, default=0)
    parser.add_argument('--generator', choices=['original', 'rcm'], default='original')
    parser.add_argument('--vae', choices=['original', 'tiny-decode', 'tiny-both'], default='original')
    parser.add_argument('--decoder-comparison', action='store_true')
    parser.add_argument('--conditioning', choices=['full-mask', 'masked-body', 'masked-body-open-canvas'], default='full-mask')
    parser.add_argument('--steps', type=int, choices=[1, 2, 4, 20, 30, 50], default=30)
    parser.add_argument('--context-scale', type=float, choices=[.5, 1., 1.5], default=1.)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    args.height = args.size
    args.width = args.size if args.aspect == 'square' else (args.size * 2 // 3 // 16 * 16)
    args.trajectory_frames = args.trajectory_frames or args.frames
    if args.frame_offset < 0 or args.frame_offset + args.frames > args.trajectory_frames:
        parser.error('The rendered frame range must fit the requested trajectory.')
    if (args.generator == 'rcm') != (args.steps in (1, 2, 4)):
        parser.error('rCM requires 1/2/4 steps; original baseline requires 20/30/50 steps.')
    if args.decoder_comparison and (args.generator != 'rcm' or args.vae != 'original'):
        parser.error('Decoder comparison requires rCM and original VAE.')
    args.pose_format = 'full-body'
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a fresh lowercase experiment label.')
    manifest = json.loads((ROOT / 'config/vace-benchmark.json').read_text(encoding='utf-8'))
    sys.path.insert(0, str(ROOT))
    preflight(manifest, args.prepare_only, rcm=args.generator == 'rcm', tiny=args.vae != 'original' or args.decoder_comparison)
    output = ROOT / 'generated/local-app/audit' / ('vace-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'complete': False, 'settings': vars(args), 'model_revision': manifest['files'][0]['revision'],
              'code_revision': manifest['wan_code']['revision'], 'scope': 'Offline pose/control quality; no live streaming, speech or command planner',
              'api_cost_usd': 0, 'live_app_selected': False}
    try:
        run(args, record, output, manifest)
    except Exception as error:
        record['error_type'], record['error'] = type(error).__name__, str(error)[:1000]
        raise
    finally:
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
