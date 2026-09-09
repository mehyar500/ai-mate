"""Single-GPU Windows benchmark of the pinned upstream OmniAvatar runner.

Uses the existing local model cache. Never submits prompts to a hosted model.
This is an experimental motion benchmark, not the interactive app renderer.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / '.cache/local-poc/OmniAvatar'
REVISION = '1536bf31abaec74364fb7d5883470d5b23ffa7f8'


def patch_single_gpu(root):
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise RuntimeError('Upstream revision changed; review the Windows compatibility patch first.')
    path = root / 'scripts/inference.py'
    original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:scripts/inference.py'], text=True, encoding='utf-8')
    start = original.index('        dist.init_process_group(')
    end = original.index("        ckpt_path =", start)
    # Sequence parallelism and NCCL are not needed with exactly one GPU.
    patched = original[:start] + '        assert args.sp_size == 1 and args.world_size == 1\n        torch.cuda.set_device(args.rank)\n' + original[end:]
    patched = patched.replace('dist.get_rank()', 'args.rank').replace('        dist.barrier()', '        # No distributed barrier in single-GPU inference.')
    current = path.read_text(encoding='utf-8')
    if current not in (original, patched):
        raise RuntimeError('Unrecognized upstream edits; refusing to overwrite them.')
    path.write_text(patched, encoding='utf-8')

    path = root / 'OmniAvatar/utils/io_utils.py'
    original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:OmniAvatar/utils/io_utils.py'], text=True, encoding='utf-8')
    patched = 'import shutil\n' + original
    replacements = {
        'subprocess.run([f"cp {tmp_save_path} {now_save_path}"], check=True, shell=True)':
            'shutil.copyfile(tmp_save_path, now_save_path)',
        'subprocess.check_call(cmd, stdout=None, stdin=subprocess.PIPE, shell=True)':
            'subprocess.run(["ffmpeg", "-y", "-i", tmp_save_path, "-i", audio_path, "-v", "error", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", tmp_save_path[:-4]+"_wav.mp4"], check=True)',
        'subprocess.run([f"cp {tmp_save_path[:-4]}_wav.mp4 {now_save_path[:-4]}_wav.mp4"], check=True, shell=True)':
            'shutil.copyfile(tmp_save_path[:-4]+"_wav.mp4", now_save_path[:-4]+"_wav.mp4")',
    }
    for before, after in replacements.items():
        if patched.count(before) != 1:
            raise RuntimeError('Upstream exporter changed; review the Windows patch.')
        patched = patched.replace(before, after)
    if path.read_text(encoding='utf-8') not in (original, patched):
        raise RuntimeError('Unrecognized exporter edits; refusing to overwrite them.')
    path.write_text(patched, encoding='utf-8')
    path = root / 'OmniAvatar/models/wan_video_dit.py'
    original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:OmniAvatar/models/wan_video_dit.py'], text=True, encoding='utf-8')
    start = original.index('from xfuser.core.distributed import')
    end = original.index('\ntry:', start)
    patched = original[:start] + 'if args.sp_size > 1:\n' + '\n'.join('    ' + line for line in original[start:end].splitlines()) + original[end:]
    if path.read_text(encoding='utf-8') not in (original, patched):
        raise RuntimeError('Unrecognized DiT edits; refusing to overwrite them.')
    path.write_text(patched, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--prompt', default='Full body view of an adult woman standing in a garden. She raises her right hand and waves hello while speaking. Static camera, natural body movement.')
    parser.add_argument('--steps', type=int, default=10)
    parser.add_argument('--height', type=int, default=384)
    parser.add_argument('--width', type=int, default=256)
    parser.add_argument('--frames', type=int, default=81)
    parser.add_argument('--guidance', type=float, default=4.5)
    parser.add_argument('--audio-guidance', type=float)
    parser.add_argument('--resident-parameters', type=int, default=2000000000,
                        help='DiT parameters kept on GPU during denoising; 0 enables full CPU offload.')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--wait-models', type=int, default=0, help='Seconds to wait for the existing downloader; does not start another download.')
    opts = parser.parse_args()
    if any(x < 128 or x % 16 for x in (opts.height, opts.width)):
        parser.error('Dimensions must be multiples of 16, at least 128.')
    if opts.frames < 17 or opts.frames % 4 != 1 or not 1 <= opts.steps <= 50:
        parser.error('Frames must be 4n+1, at least 17; steps must be 1–50.')
    if any(s in opts.prompt for s in ('@@', '\n', '\r')):
        parser.error('Prompt must be one line without @@ delimiters.')
    for path in (opts.image, opts.audio):
        if not path.is_file():
            parser.error(f'Missing input: {path}')
    patch_single_gpu(UPSTREAM)
    import yaml
    config = yaml.safe_load((UPSTREAM / 'configs/inference_1.3B.yaml').read_text(encoding='utf-8'))
    config.update(image_sizes_720=[[opts.height, opts.width]], max_hw=720,
                  max_tokens=(opts.frames + 3) * opts.height * opts.width // 1024,
                  num_steps=opts.steps, seq_len=opts.frames, sp_size=1,
                  guidance_scale=opts.guidance, audio_scale=opts.audio_guidance,
                  num_persistent_param_in_dit=opts.resident_parameters, silence_duration_s=0, use_fsdp=False)
    config_path = UPSTREAM / 'configs/local_windows.yaml'
    config_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    input_path = UPSTREAM / 'local_motion_input.txt'
    input_path.write_text(f'{opts.prompt}@@{opts.image.resolve().as_posix()}@@{opts.audio.resolve().as_posix()}\n', encoding='utf-8')
    if opts.prepare_only:
        print('Single-GPU port and benchmark inputs prepared.')
        return
    required = ['Wan2.1-T2V-1.3B/diffusion_pytorch_model.safetensors',
                'Wan2.1-T2V-1.3B/models_t5_umt5-xxl-enc-bf16.pth',
                'Wan2.1-T2V-1.3B/Wan2.1_VAE.pth', 'OmniAvatar-1.3B/pytorch_model.pt',
                'wav2vec2-base-960h/config.json', 'wav2vec2-base-960h/preprocessor_config.json']
    deadline = time.monotonic() + opts.wait_models
    while True:
        missing = [name for name in required if not (UPSTREAM / 'pretrained_models' / name).is_file()]
        audio_root = UPSTREAM / 'pretrained_models/wav2vec2-base-960h'
        if not any((audio_root / name).is_file() for name in ('model.safetensors', 'pytorch_model.bin')):
            missing.append('wav2vec2-base-960h weights')
        if not missing or time.monotonic() >= deadline:
            break
        print('Waiting for existing download: ' + ', '.join(missing), flush=True)
        time.sleep(min(30, max(0, deadline-time.monotonic())))
    if missing:
        raise RuntimeError('Model download is incomplete: ' + ', '.join(missing))
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['RANK'] = os.environ['LOCAL_RANK'] = '0'
    os.environ['WORLD_SIZE'] = '1'
    import torch
    torch.set_num_threads(4)
    torch.cuda.reset_peak_memory_stats()
    print(f'GPU: {torch.cuda.get_device_name()}; steps={opts.steps}; {opts.width}x{opts.height}; frames={opts.frames}', flush=True)
    os.chdir(UPSTREAM)
    sys.path.insert(0, str(UPSTREAM))
    sys.argv = ['inference.py', '--config', str(config_path), '--input_file', str(input_path), '--infer']
    started = time.perf_counter()
    completed = False
    try:
        runpy.run_path(str(UPSTREAM / 'scripts/inference.py'), run_name='__main__')
        completed = True
    finally:
        record = {'completed': completed, 'wall_s': round(time.perf_counter() - started, 3),
                  'peak_allocated_gib': round(torch.cuda.max_memory_allocated() / 2**30, 3),
                  'steps': opts.steps, 'resolution': [opts.width, opts.height], 'upstream': REVISION}
        (UPSTREAM / 'last_benchmark.json').write_text(json.dumps(record, indent=2))
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
