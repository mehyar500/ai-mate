"""Isolated, non-explicit fresh-motion test of the pinned LongLive 2.0 release.

Uses upstream inference (Apache-2.0) with memory-conscious loading, native
PyTorch attention, and local FFmpeg. Never reads conversations or changes the
live app. Pre-encoded prompts are reported separately from generation timing.
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
import types

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / '.cache/local-poc/LongLive2'
WEIGHTS = ROOT / '.cache/local-poc/longlive2-models'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preflight(manifest, light_vae=False, s2=False):
    revision = subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != manifest['code']['revision']:
        raise ValueError('Unexpected LongLive code revision.')
    expected = (ROOT / 'config/longlive2-windows.patch').read_bytes().replace(b'\r\n', b'\n')
    actual = subprocess.check_output(['git', '-C', str(CODE), 'diff', '--no-ext-diff', '--unified=0']).replace(b'\r\n', b'\n')
    if actual != expected:
        raise ValueError('LongLive source must have only the recorded compatibility patch.')
    rows = manifest['files'] + (manifest.get('optional_files', []) if light_vae else [])
    rows += manifest.get('two_step_files', []) if s2 else []
    for row in rows:
        path = WEIGHTS / row['folder'] / row['filename']
        if not path.is_file() or path.stat().st_size != row['size']:
            raise ValueError('Missing/incomplete weight: ' + row['filename'])
        if checksum(path) != row['sha256']:
            raise ValueError('Unverified weight: ' + row['filename'])


def sdpa_attention(q, k, v, q_lens=None, k_lens=None, dropout_p=0.,
                   softmax_scale=None, q_scale=None, causal=False,
                   window_size=(-1, -1), deterministic=False, dtype=None, **kwargs):
    """Dense inference attention; reject unsupported semantics rather than ignore them."""
    import torch
    if window_size != (-1, -1) or q_lens is not None or k_lens is not None:
        raise ValueError('This benchmark requires dense, unpadded attention.')
    if deterministic or dropout_p or kwargs:
        raise ValueError('Unsupported attention option in the isolated benchmark.')
    dtype = dtype or q.dtype
    result = torch.nn.functional.scaled_dot_product_attention(
        (q if q_scale is None else q * q_scale).transpose(1, 2).to(dtype),
        k.transpose(1, 2).to(dtype), v.transpose(1, 2).to(dtype),
        is_causal=causal, scale=softmax_scale)
    return result.transpose(1, 2).contiguous().to(q.dtype)


def prompt_pair(case):
    setting = ('A continuous realistic video of the same adult woman in a cream sweater, '
               'blue jeans and white shoes standing in the same garden. Fixed camera, '
               'full body visible, natural human anatomy, calm background, no cuts. ')
    if case == 'raise-lower':
        return [setting + 'She slowly raises her right hand beside her shoulder, palm facing the camera. Her left arm stays down.',
                setting + 'She gently lowers her raised right hand to her side and stands still with both arms down.']
    if case == 'unilateral-raise-lower':
        return [setting + 'Her left hand rests against her left thigh throughout. Only her right elbow bends, '
                'lifting her right hand on the LEFT side of the picture to shoulder height. One hand is raised, the other stays at her thigh.',
                setting + 'Both hands now rest against her thighs. Her right elbow straightens and her right hand '
                'descends on the LEFT side of the picture until it rests against her right thigh. She keeps both hands down.']
    return [setting + 'She slowly turns her whole body sideways to her left while keeping both feet on the ground.',
            setting + 'She turns her whole body back to face the camera, then stands still.']


def install_streaming_vae(model):
    """Continue the official causal Wan decoder without clearing between chunks.

    Adapted from WanVAE_.decode in the pinned Apache-2.0 LongLive release.
    No weights or neural layers change. Call clear_cache for each new video.
    """
    import torch
    from wan_5b.modules.vae2_2 import unpatchify
    original_clear = model.clear_cache

    def clear(self):
        original_clear()
        self._benchmark_stream_started = False

    def cached_decode(self, z, scale):
        if isinstance(scale[0], torch.Tensor):
            z = z / scale[1].view(1, self.z_dim, 1, 1, 1) + scale[0].view(1, self.z_dim, 1, 1, 1)
        else:
            z = z / scale[1] + scale[0]
        x = self.conv2(z)
        frames = []
        for index in range(x.shape[2]):
            self._conv_idx = [0]
            frames.append(self.decoder(x[:, :, index:index + 1], feat_cache=self._feat_map,
                                       feat_idx=self._conv_idx, first_chunk=not self._benchmark_stream_started))
            self._benchmark_stream_started = True
        return unpatchify(torch.cat(frames, dim=2), patch_size=2)

    model.clear_cache = types.MethodType(clear, model)
    model.cached_decode = types.MethodType(cached_decode, model)
    model.clear_cache()


def run(args, record, output):
    # Isolated optional dependencies; do not alter application packages.
    sys.path[:0] = [str(ROOT / '.cache/longlive2-deps'), str(CODE), str(ROOT)]
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    # Explicit portable baseline; upstream enables optional Triton kernels by default.
    os.environ['LLV2_TRITON_ADALN'] = '0'
    os.environ['LLV2_TRITON_ROPE'] = '0'
    record['triton_kernels'] = False
    import numpy as np
    import torch
    from PIL import Image
    from omegaconf import OmegaConf
    from pipeline import CausalDiffusionInferencePipeline
    from utils.config import normalize_config
    from utils.scheduler import FlowMatchScheduler
    from utils.wan_5b_wrapper import WanDiffusionWrapper, WanVAEWrapper
    from wan_5b.modules.causal_model import CausalWanModel
    from wan_5b.modules.t5 import umt5_xxl
    from wan_5b.modules.tokenizers import HuggingfaceTokenizer
    import wan_5b.modules.attention as attention_module
    import wan_5b.modules.causal_model as causal_module
    import wan_5b.modules.model as model_module

    torch.set_num_threads(8)
    torch.set_grad_enabled(False)
    dtype = torch.bfloat16
    device = torch.device('cuda')
    if not torch.cuda.is_available():
        raise RuntimeError('A CUDA GPU is required.')
    free, total = torch.cuda.mem_get_info()
    record['gpu'] = {'name': torch.cuda.get_device_name(), 'free_bytes_before': free, 'total_bytes': total}
    if free < 14_000_000_000:
        raise RuntimeError('Close idle GPU inference workers before this isolated benchmark; 14GB free required.')
    for module in (attention_module, causal_module, model_module):
        module.flash_attention = sdpa_attention
        module.attention = sdpa_attention
    os.chdir(WEIGHTS)  # Upstream VAE paths are relative to wan_models/.
    base = WEIGHTS / 'wan_models/Wan2.2-TI2V-5B'
    prompts = prompt_pair(args.case)
    record['prompts'] = prompts
    embeddings_path = WEIGHTS / ('embeddings-' + hashlib.sha256(json.dumps(prompts).encode()).hexdigest()[:16] + '.safetensors')
    from safetensors.torch import load_file, save_file
    started = time.perf_counter()
    if embeddings_path.exists():
        encoded = load_file(str(embeddings_path))
        record['prompt_cache_hit'] = True
    else:
        text_device = torch.device(args.text_device)
        with torch.device('meta'):
            encoder = umt5_xxl(encoder_only=True, return_tokenizer=False, dtype=dtype, device='meta')
        state = torch.load(base / 'models_t5_umt5-xxl-enc-bf16.pth', weights_only=True, map_location='cpu', mmap=True)
        encoder.load_state_dict(state, assign=True)
        del state
        encoder.eval().requires_grad_(False).to(device=text_device, dtype=dtype)
        tokenizer = HuggingfaceTokenizer(str(base / 'google/umt5-xxl'), seq_len=512, clean='whitespace', local_files_only=True)
        encoded = {}
        for i, prompt in enumerate(prompts):
            began = time.perf_counter()
            ids, mask = tokenizer([prompt], return_mask=True, add_special_tokens=True)
            context = encoder(ids.to(text_device), mask.to(text_device))
            context[:, int(mask.sum()):] = 0
            encoded[str(i)] = context.cpu().contiguous()
            print(json.dumps({'prompt_encoded': i, 'seconds': time.perf_counter() - began}), flush=True)
        save_file(encoded, str(embeddings_path))
        del encoder, tokenizer, context, ids, mask
        gc.collect()
        torch.cuda.empty_cache()
        record['prompt_cache_hit'] = False
    record['prompt_preparation_s'] = time.perf_counter() - started

    class EncodedText(torch.nn.Module):
        def forward(self, text_prompts):
            return {'prompt_embeds': torch.cat([encoded[str(prompts.index(p))] for p in text_prompts]).to(device)}

    class LoadedGenerator(WanDiffusionWrapper):
        def __init__(self):
            # Upstream wrapper initialization, avoiding a duplicate base-model download.
            torch.nn.Module.__init__(self)
            config = json.loads((base / 'config.json').read_text(encoding='utf-8'))
            with torch.device('meta'):
                self.model = CausalWanModel.from_config(config, local_attn_size=args.attention_frames, sink_size=8,
                                                       num_frame_per_block=8)
            # Upstream deliberately leaves rotary frequencies unregistered, so
            # load_state_dict(assign=True) cannot materialize this meta tensor.
            d = self.model.dim // self.model.num_heads
            self.model.freqs = torch.cat([model_module.rope_params(1024, d - 4 * (d // 6)),
                                         model_module.rope_params(1024, 2 * (d // 6)),
                                         model_module.rope_params(1024, 2 * (d // 6))], dim=1)
            self.model.t_scale, self.model.rope_method = 1.0, 'linear'
            self.model.original_seq_len = None
            self.uniform_timestep = False
            self.scheduler = FlowMatchScheduler(shift=5.0, sigma_min=0.0, extra_one_step=True)
            self.scheduler.set_timesteps(1000, training=True)
            self.seq_len = 8 * (args.width // 32) * (args.height // 32)
            self._compiled_model_call = None
            self.post_init()
            checkpoint_file = ('generator-s2/model_4o6.pt' if args.checkpoint == 's2-dequantized'
                               else 'generator/model_bf16.pt')
            state = torch.load(WEIGHTS / checkpoint_file, weights_only=True, mmap=True, map_location='cpu')
            if args.checkpoint == 's2-dequantized':
                from scripts.longlive2_s2 import unpack_checkpoint
                state, record['s2_conversion'] = unpack_checkpoint(state, CODE)
                print(json.dumps({'s2_conversion': record['s2_conversion']}), flush=True)
            elif 'generator' in state:
                state = state['generator']
            elif 'model' in state:
                state = state['model']
            self.load_state_dict(state, assign=True, strict=True)
            del state
            self.eval().requires_grad_(False).to(device=device, dtype=dtype)

    vae = WanVAEWrapper().eval().requires_grad_(False).to(device=device, dtype=dtype)
    reference = ROOT / 'generated/local-app/fullbody.png'
    record['reference_sha256'] = checksum(reference)
    im = Image.open(reference).convert('RGB').resize((args.width, args.height), Image.Resampling.LANCZOS)
    pixels = torch.from_numpy(np.asarray(im).copy()).permute(2, 0, 1)[None, :, None].to(device=device, dtype=dtype) / 127.5 - 1
    with torch.autocast('cuda', dtype=dtype):
        initial = vae.encode_to_latent(pixels).to(dtype)
    del pixels
    if args.vae == 'light-v2':
        del vae
        gc.collect()
        torch.cuda.empty_cache()
        from utils.lightvae_5b_wrapper import LightVAE5BWrapper
        vae = LightVAE5BWrapper(str(WEIGHTS / 'wan_models/Matrix-Game-3.0/MG-LightVAE_v2.pth'), device=device, dtype=dtype)
    else:
        install_streaming_vae(vae.model)
    began = time.perf_counter()
    generator = LoadedGenerator()
    record['generator_load_s'] = time.perf_counter() - began
    print(json.dumps({'generator_loaded_s': record['generator_load_s']}), flush=True)
    if args.precision == 'fp8-selective':
        from scripts.longlive2_fp8 import quantize_blocks
        began = time.perf_counter()
        record['quantized_linear_count'] = quantize_blocks(generator.model, skip_ffn_output=True)
        torch.cuda.synchronize()
        record['quantization_s'] = time.perf_counter() - began
        gc.collect()
        torch.cuda.empty_cache()
        print(json.dumps({'quantized_linear_count': record['quantized_linear_count'],
                          'quantization_s': record['quantization_s']}), flush=True)
    config = normalize_config(OmegaConf.create({
        'model_kwargs': {'model_name': 'Wan2.2-TI2V-5B', 'timestep_shift': 5., 'num_frame_per_block': 8,
                         'local_attn_size': args.attention_frames},
        'data': {'image_or_video_shape': [1, args.blocks * 8, 48, args.height // 16, args.width // 16]},
        'inference': {'sampling_steps': args.sampling_steps, 'independent_first_frame': True, 'sink_size': 8, 'guidance_scale': 1.,
                      'multi_shot_sink': False, 'streaming_vae': True, 'async_vae': False},
    }))
    pipe = CausalDiffusionInferencePipeline(config, device, generator=generator, text_encoder=EncodedText(), vae=vae)
    record['effective_sampling_steps'] = pipe.sampling_steps
    record['sampling_scope'] = ('released merged BF16 checkpoint at four steps' if args.sampling_steps == 4 else
                                'reduced-step ablation of the four-step checkpoint; not the separately trained NVFP4-S2 model')
    if args.checkpoint == 's2-dequantized':
        record['sampling_scope'] = 'trained NVFP4-S2 weights dequantized to BF16; BF16 activations; not native NVFP4'
    blocks = [prompts[0]] * (args.blocks // 2) + [prompts[1]] * (args.blocks // 2)
    record['runs'] = []
    original_decode = vae.model.cached_decode
    decoded_events = []
    inference_start = None

    def timed_decode(*inputs, **kwargs):
        result = original_decode(*inputs, **kwargs)
        torch.cuda.synchronize()
        event = {'ready_s': time.perf_counter() - inference_start, 'frames': result.shape[2]}
        decoded_events.append(event)
        print(json.dumps({'decoded_chunk': event}), flush=True)
        return result

    vae.model.cached_decode = timed_decode
    for i in range(args.repeats):
        decoded_events.clear()
        torch.cuda.reset_peak_memory_stats()
        rng = torch.Generator(device=device).manual_seed(args.seed)
        noise = torch.randn(1, args.blocks * 8, 48, args.height // 16, args.width // 16,
                            generator=rng, device=device, dtype=dtype)
        torch.cuda.synchronize()
        inference_start = time.perf_counter()
        with torch.autocast('cuda', dtype=dtype):
            video = pipe.inference(noise, [blocks], initial_latent=initial)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - inference_start
        if not torch.isfinite(video).all():
            raise ValueError('Renderer produced non-finite pixels.')
        frames = (video[0].permute(0, 2, 3, 1).cpu().float().clamp(0, 1).numpy() * 255).round().astype(np.uint8)
        path = output / f'run-{i}.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                        '-video_size', f'{args.width}x{args.height}', '-framerate', '24', '-i', 'pipe:0',
                        '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(path)],
                       input=frames.tobytes(), check=True, timeout=60)
        row = {'inference_s': elapsed, 'generated_frames': len(frames), 'generated_fps': len(frames) / elapsed,
               'first_decoded_chunk_s': decoded_events[0]['ready_s'] if decoded_events else None,
               'decoded_chunks': list(decoded_events), 'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
               'peak_reserved_bytes': torch.cuda.max_memory_reserved(), 'file': path.name, 'sha256': checksum(path)}
        record['runs'].append(row)
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(row), flush=True)
        del video, frames, noise
    record['complete'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--case', choices=['raise-lower', 'unilateral-raise-lower', 'turn-return'], default='raise-lower')
    parser.add_argument('--sampling-steps', type=int, choices=[2, 4], default=4)
    parser.add_argument('--checkpoint', choices=['bf16', 's2-dequantized'], default='bf16')
    parser.add_argument('--blocks', type=int, choices=[2, 4], default=2)
    parser.add_argument('--attention-frames', type=int, choices=[16, 32], default=16)
    parser.add_argument('--precision', choices=['bf16', 'fp8-selective'], default='bf16')
    parser.add_argument('--width', type=int, choices=[256, 320, 384], default=320)
    parser.add_argument('--height', type=int, choices=[384, 480, 576], default=480)
    parser.add_argument('--repeats', type=int, choices=[1, 2], default=2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--text-device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--vae', choices=['wan', 'light-v2'], default='wan')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a new lowercase experiment label.')
    if args.checkpoint == 's2-dequantized' and (args.sampling_steps != 2 or args.precision != 'bf16'):
        parser.error('The S2 diagnostic requires two steps and BF16 compute.')
    manifest = json.loads((ROOT / 'config/longlive2-benchmark.json').read_text(encoding='utf-8'))
    preflight(manifest, light_vae=args.vae == 'light-v2', s2=args.checkpoint == 's2-dequantized')
    output = ROOT / 'generated/local-app/audit' / ('longlive2-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'complete': False, 'settings': vars(args), 'model_revision': manifest['files'][0]['revision'],
              'code_revision': manifest['code']['revision'], 'scope': 'fresh motion only; no speech, live input or browser transport',
              'api_cost_usd': 0, 'commercial_service_qualified': False}
    if args.checkpoint == 's2-dequantized':
        record['model_revision'] = manifest['two_step_files'][0]['revision']
    try:
        run(args, record, output)
    except Exception as error:
        record['error_type'] = type(error).__name__
        record['error'] = str(error)[:1000]
        raise
    finally:
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
