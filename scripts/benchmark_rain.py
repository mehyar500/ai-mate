"""Isolated RAIN renderer test with measured, synthetic right/left arm controls.

This tests pose-to-video, not natural-language planning or a complete call.
Never reads conversation history, starts a server, or selects a live model.
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
CODE = ROOT / '.cache/local-poc/RAIN'
WEIGHTS = ROOT / '.cache/local-poc/rain-models'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preflight(manifest, prepare_only):
    revision = subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != manifest['code']['revision'] or subprocess.check_output(['git', '-C', str(CODE), 'diff', '--no-ext-diff']):
        raise ValueError('Expected the clean, pinned RAIN checkout.')
    rows = [(WEIGHTS / row['folder'] / row['filename'], row) for row in manifest['pose_files']]
    if not prepare_only:
        rows += [(WEIGHTS / row['folder'] / row['filename'], row) for row in manifest['files']]
        rows += [(ROOT / row['path'], row) for row in manifest['reused_local_files']]
    for path, row in rows:
        if not path.is_file() or path.stat().st_size != row['size'] or checksum(path) != row['sha256']:
            raise ValueError('Missing or unverified asset: ' + path.name)


def controls(args, output, record):
    import numpy as np
    from PIL import Image, ImageOps
    from src.dwpose import draw_pose
    from src.dwpose.wholebody import Wholebody

    reference_path = ROOT / 'generated/local-app/fullbody.png'
    record['reference_sha256'] = checksum(reference_path)
    reference = ImageOps.pad(Image.open(reference_path).convert('RGB'), (args.size, args.size),
                             method=Image.Resampling.LANCZOS, color=(0, 0, 0))
    reference.save(output / 'reference.png')
    detector = Wholebody(str(WEIGHTS / 'dwpose/yolox_l.onnx'), str(WEIGHTS / 'dwpose/dw-ll_ucoco_384.onnx'),
                         ['CPUExecutionProvider'])
    started = time.perf_counter()
    points, scores = detector(np.asarray(reference))
    record['reference_pose_s'] = time.perf_counter() - started
    if points.shape != (1, 134, 2) or scores.shape != (1, 134):
        raise ValueError('Expected one complete DWPose reference skeleton.')
    points = points[0] / args.size
    scores = scores[0]
    shoulder, elbow, wrist = (2, 3, 4) if args.side == 'right' else (5, 6, 7)
    hand = slice(113, 134) if args.side == 'right' else slice(92, 113)
    if min(scores[[shoulder, elbow, wrist]]) < .3:
        raise ValueError('Reference arm has uncertain landmarks.')
    upper, lower = points[elbow] - points[shoulder], points[wrist] - points[elbow]
    hand_offsets = points[hand] - points[wrist]
    sign = 1 if args.side == 'right' else -1

    def rotate(vectors, angle):
        c, s = np.cos(angle), np.sin(angle)
        return vectors @ np.array([[c, s], [-s, c]])

    frames, trajectories = [], []
    for i in range(args.frames):
        phase = i / (args.frames - 1)
        progress = min(1., phase * 4) if phase < .5 else max(0., 3 - phase * 4)
        progress = progress * progress * (3 - 2 * progress)
        if args.motion == 'static':
            progress = 0.
        moved = points.copy()
        moved[elbow] = points[shoulder] + rotate(upper, sign * np.deg2rad(70) * progress)
        moved[wrist] = moved[elbow] + rotate(lower, sign * np.deg2rad(160) * progress)
        moved[hand] = moved[wrist] + rotate(hand_offsets, sign * np.deg2rad(160) * progress)
        if ((moved[[shoulder, elbow, wrist]] < 0) | (moved[[shoulder, elbow, wrist]] > 1)).any():
            raise ValueError('Control arm leaves the reference frame.')
        trajectories.append(moved.copy())
        moved[scores < .3] = -1
        subset = np.where(scores[:18] > .3, np.arange(18), -1)[None]
        pose = {'bodies': {'candidate': moved[:18], 'subset': subset}, 'faces': moved[None, 24:92],
                'hands': np.stack([moved[92:113], moved[113:134]])}
        canvas = draw_pose(pose, args.size, args.size, [], None, args.pose_format == 'face-only')
        frames.append(Image.fromarray(canvas))
    trajectory = np.stack(trajectories)
    for i in sorted({0, args.frames // 4, args.frames // 2, args.frames - 1}):
        frames[i].save(output / f'control-{i:03}.png')
    lengths = np.stack([np.linalg.norm(trajectory[:, elbow] - trajectory[:, shoulder], axis=-1),
                        np.linalg.norm(trajectory[:, wrist] - trajectory[:, elbow], axis=-1)])
    record['controls'] = {'side': args.side, 'frames': args.frames, 'size': args.size,
                          'max_arm_length_deviation': float(np.abs(lengths - lengths[:, :1]).max()),
                          'type': ('static reference pose' if args.motion == 'static' else
                                   'deterministic joint-angle raise, hold, lower; no language planner'),
                          'pose_format': args.pose_format,
                          'other_body_points_fixed': True}
    np.savez_compressed(output / 'controls.npz', points=trajectory, scores=scores)
    del detector
    gc.collect()
    return reference, frames


def run(args, output, record):
    sys.path[:0] = [str(ROOT / '.cache/rain-deps'), str(ROOT / '.cache/longlive2-deps'), str(CODE)]
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    reference, poses = controls(args, output, record)
    if args.prepare_only:
        record['controls_prepared'] = True
        return
    import numpy as np
    import torch
    from diffusers import AutoencoderKL
    from transformers import CLIPVisionConfig, CLIPVisionModelWithProjection
    from omegaconf import OmegaConf
    from src.pipeline.pipeline_pose2vid_lcm import Pose2VideoPipelineLCM
    from src.models.unet_2d_condition import UNet2DConditionModel
    from src.models.unet_3d import UNet3DConditionModel
    from src.models.pose_guider import PoseGuider
    from src.scheduler.scheduler_lcm import LCMScheduler

    torch.set_grad_enabled(False)
    torch.set_num_threads(8)
    if not torch.cuda.is_available() or torch.cuda.mem_get_info()[0] < 13_000_000_000:
        raise RuntimeError('Exclusive test requires a CUDA GPU with 13GB free.')
    dtype = torch.float16
    started = time.perf_counter()
    cfg = OmegaConf.load(CODE / 'configs/rain_morpher.yaml')

    def loaded(module, path):
        state = torch.load(path, weights_only=True, mmap=True, map_location='cpu')
        # Older CLIP saves this deterministic buffer; newer versions regenerate it.
        key = 'vision_model.embeddings.position_ids'
        if isinstance(module, CLIPVisionModelWithProjection) and key in state:
            expected = module.vision_model.embeddings.position_ids.cpu()
            if not torch.equal(state[key], expected):
                raise ValueError('CLIP position IDs differ from the regenerated buffer.')
            del state[key]
            record['clip_position_ids_verified'] = True
        module.load_state_dict(state, assign=True, strict=True)
        del state
        return module.eval().requires_grad_(False).to(device='cuda', dtype=dtype)

    vae = AutoencoderKL.from_pretrained(ROOT / '.cache/local-poc/sd-vae', local_files_only=True,
                                       use_safetensors=True, torch_dtype=dtype).to('cuda')
    image_encoder = loaded(CLIPVisionModelWithProjection(CLIPVisionConfig.from_json_file(
        str(WEIGHTS / 'clip/image_encoder/config.json'))), WEIGHTS / 'clip/image_encoder/pytorch_model.bin')
    reference_unet = loaded(UNet2DConditionModel.from_config(str(CODE / 'configs/unet.json')),
                            WEIGHTS / 'rain/reference_unet.pth')
    pose_guider = loaded(PoseGuider(conditioning_embedding_channels=320, block_out_channels=(16, 32, 96, 256)),
                         WEIGHTS / 'rain/pose_guider.pth')
    model_config = json.loads((CODE / 'configs/unet.json').read_text(encoding='utf-8'))
    model_config.update({'down_block_types': ['CrossAttnDownBlock3D'] * 3 + ['DownBlock3D'],
                         'up_block_types': ['UpBlock3D'] + ['CrossAttnUpBlock3D'] * 3,
                         'mid_block_type': 'UNetMidBlock3DCrossAttn'})
    denoiser = loaded(UNet3DConditionModel.from_config(model_config, **OmegaConf.to_container(cfg.unet_additional_kwargs)),
                      WEIGHTS / 'rain/motion_unet.pth')
    scheduler = LCMScheduler(**cfg.noise_scheduler_kwargs)
    scheduler.to(torch.device('cuda'))
    pipe = Pose2VideoPipelineLCM(vae, image_encoder, reference_unet, denoiser, pose_guider, scheduler).to('cuda')
    record['models_loaded_s'] = time.perf_counter() - started
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    started = time.perf_counter()
    video = pipe(ref_image=reference, pose_images=poses, width=args.size, height=args.size, video_length=args.frames,
                 num_inference_steps=4, guidance_scale=3.5, generator=torch.Generator('cuda').manual_seed(args.seed)).videos
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    if not torch.isfinite(video).all():
        raise ValueError('Renderer produced non-finite pixels.')
    frames = (video[0].permute(1, 2, 3, 0).cpu().float().clamp(0, 1).numpy() * 255).round().astype(np.uint8)
    path = output / 'run-0.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size',
                    f'{args.size}x{args.size}', '-framerate', '16', '-i', 'pipe:0', '-an', '-c:v', 'libx264',
                    '-crf', '18', '-pix_fmt', 'yuv420p', str(path)], input=frames.tobytes(), check=True, timeout=60)
    record.update({'complete': True, 'inference_s': elapsed, 'frames': len(frames), 'generated_fps': len(frames) / elapsed,
                   'peak_allocated_bytes': torch.cuda.max_memory_allocated(), 'file': path.name, 'sha256': checksum(path)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--side', choices=['right', 'left'], default='right')
    parser.add_argument('--motion', choices=['raise-lower', 'static'], default='raise-lower')
    parser.add_argument('--pose-format', choices=['full-body', 'face-only'], default='full-body')
    parser.add_argument('--size', type=int, choices=[384, 512], default=512)
    parser.add_argument('--frames', type=int, choices=[16, 32, 64], default=32)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a fresh lowercase experiment label.')
    manifest = json.loads((ROOT / 'config/rain-benchmark.json').read_text(encoding='utf-8'))
    preflight(manifest, args.prepare_only)
    output = ROOT / 'generated/local-app/audit' / ('rain-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'complete': False, 'settings': vars(args), 'api_cost_usd': 0,
              'scope': 'offline pose-driven renderer experiment; no speech or browser call', 'live_app_selected': False}
    try:
        run(args, output, record)
    except Exception as error:
        record.update({'error_type': type(error).__name__, 'error': str(error)[:1000]})
        raise
    finally:
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
