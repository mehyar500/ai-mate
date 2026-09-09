"""Offline SyncNet diagnostics for retained synthetic call recordings only.

This is a calibrated timing diagnostic, not human perceptual acceptance. It
never alters the running app, its audio timing, or its private conversation.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/local-poc/syncnet-evaluator'
MANIFEST = ROOT / 'config/syncnet-evaluator.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def displayed_indices(timestamps, count, fps=25):
    """Hold the actual displayed frame at each evaluation timestamp; don't speed it up."""
    timestamps = np.asarray(timestamps, dtype=np.float64)
    if (len(timestamps) < 2 or not np.isfinite(timestamps).all()
            or timestamps[0] != 0 or np.any(np.diff(timestamps) <= 0)
            or count < 5 or fps <= 0):
        raise ValueError('Invalid decoded video timeline.')
    grid = np.arange(count) / fps
    if grid[-1] > timestamps[-1] + np.median(np.diff(timestamps)):
        raise ValueError('Evaluation extends beyond the last displayed frame.')
    return np.maximum(0, np.searchsorted(timestamps, grid, side='right') - 1)


def shift_audio(samples, shift_samples):
    """Positive shifts delay sound. Never wrap speech from one end to the other."""
    samples = np.asarray(samples)
    if samples.ndim != 1 or abs(shift_samples) >= len(samples):
        raise ValueError('Invalid audio shift.')
    output = np.zeros_like(samples)
    if shift_samples > 0:
        output[shift_samples:] = samples[:-shift_samples]
    elif shift_samples < 0:
        output[:shift_samples] = samples[-shift_samples:]
    else:
        output[:] = samples
    return output


def offset_score(lips, audio, radius=15):
    """Use identical interior visual windows at every lag, avoiding padded-edge bias.

    Positive audio_delay_ms means the matching sound is later than the lips.
    This sign is opposite to upstream's AV-offset convention. Distances are
    not directly comparable with upstream scores that include zero padding.
    """
    lips, audio = np.asarray(lips), np.asarray(audio)
    if (lips.ndim != 2 or audio.ndim != 2 or lips.shape[1] != audio.shape[1]
            or not np.isfinite(lips).all() or not np.isfinite(audio).all()
            or not isinstance(radius, int) or radius < 1):
        raise ValueError('Invalid feature arrays.')
    length = min(len(lips), len(audio))
    if length - 2 * radius < 20:
        raise ValueError('Too little common interior speech for an offset estimate.')
    indices = np.arange(radius, length - radius)
    distances = np.asarray([
        np.linalg.norm(lips[indices] - audio[indices + lag], axis=1).mean()
        for lag in range(-radius, radius + 1)
    ])
    best = int(np.argmin(distances))
    return {
        'audio_delay_ms': (best - radius) * 40,
        'distance': float(distances[best]),
        'zero_lag_distance': float(distances[radius]),
        'confidence': float(np.median(distances) - distances[best]),
        'at_search_boundary': best in (0, 2 * radius),
        'evaluated_windows': len(indices),
        'lag_ms': list(range(-radius * 40, (radius + 1) * 40, 40)),
        'distances': distances.tolist(),
    }


def preview_idle():
    # Only read safe state. The bootstrap token is neither retained nor printed.
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=3) as response:
            state = json.load(response)
    except OSError:
        return
    if state.get('busy'):
        raise RuntimeError('Preview is busy; rerun the offline GPU review when idle.')


def load_evaluator(device):
    manifest = json.loads(MANIFEST.read_text())
    for relative, expected in manifest['runtime_sha256'].items():
        path = (CACHE / relative).resolve()
        if not path.is_relative_to(CACHE.resolve()) or digest(path) != expected:
            raise ValueError('Evaluator file missing or changed: ' + relative)
    import torch
    torch.set_num_threads(4)
    spec = importlib.util.spec_from_file_location('reviewed_syncnet', CACHE / 'SyncNetModel.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.S()
    state = torch.load(CACHE / 'syncnet_v2.model', weights_only=True, map_location='cpu')
    # Old checkpoint predates num_batches_tracked. PyTorch handles these legacy
    # BatchNorm counters when metadata is absent; all learned tensors must match.
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    sys.path.insert(0, str(CACHE))
    import python_speech_features
    return model, python_speech_features.mfcc, manifest


def load_clip(video, wav, review):
    import cv2
    from scipy.signal import medfilt, resample_poly
    from scipy.io import wavfile

    if digest(video) != review['video_sha256']:
        raise ValueError('Video changed since the every-frame review.')
    rate, pcm = wavfile.read(wav)
    if pcm.dtype != np.int16 or pcm.ndim != 1 or not 8000 <= rate <= 96000:
        raise ValueError('Expected mono PCM16 benchmark audio.')
    if not 2.2 <= len(pcm) / rate <= 15 or not np.any(pcm):
        raise ValueError('Audio is silent or outside the bounded evaluation duration.')
    common = math.gcd(rate, 16000)
    pcm = resample_poly(pcm.astype(np.float64), 16000 // common, rate // common)
    # Upstream MFCCs use PCM16-scale samples, not float samples scaled to [-1,1].
    pcm = np.clip(np.rint(pcm), -32768, 32767).astype(np.int16)
    rows = review['frames']
    if len(rows) > 400 or any(row.get('faces') != 1 or 'face_box' not in row for row in rows):
        raise ValueError('A bounded, single-face reviewed track is required.')
    boxes = np.asarray([row['face_box'] for row in rows], dtype=float)
    size = medfilt(np.maximum(boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]) / 2, 13)
    center_x = medfilt((boxes[:, 0] + boxes[:, 2]) / 2, 13)
    center_y = medfilt((boxes[:, 1] + boxes[:, 3]) / 2, 13)
    capture = cv2.VideoCapture(str(video))
    crops, timestamps = [], []
    try:
        for index, row in enumerate(rows):
            ok, frame = capture.read()
            if not ok or frame.shape[0] * frame.shape[1] > 1920 * 1920:
                raise ValueError('Video decoding did not match the reviewed frames.')
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if abs(timestamp - row['time_s']) > .002:
                raise ValueError('Decoded timestamp changed.')
            timestamps.append(timestamp)
            # Upstream asymmetric crop, crop_scale=.4, but reviewed YuNet boxes
            # replace S3FD. Retain BGR 0..255 pixels as expected by SyncNet.
            bs = size[index]
            pad = int(bs * 1.8)
            padded = np.pad(frame, ((pad, pad), (pad, pad), (0, 0)), constant_values=110)
            x, y = center_x[index] + pad, center_y[index] + pad
            face = padded[int(y-bs):int(y+bs*1.8), int(x-bs*1.4):int(x+bs*1.4)]
            if face.size == 0:
                raise ValueError('Empty face crop.')
            crops.append(cv2.resize(face, (224, 224)))
        if capture.read()[0]:
            raise ValueError('Unreviewed extra video frames.')
    finally:
        capture.release()
    count = int(len(pcm) // 640)
    indices = displayed_indices(timestamps, count)
    return np.asarray(crops)[indices], pcm, {
        'original_frames': len(rows), 'evaluation_frames': count, 'evaluation_fps': 25,
        'audio_s': len(pcm) / 16000, 'first_frame_step_ms': (timestamps[1]-timestamps[0])*1000,
        'median_face_width_px': float(np.median(boxes[:, 2]-boxes[:, 0])),
        'video_sha256': digest(video), 'audio_sha256': digest(wav),
    }


def features(model, mfcc, crops, pcm, device):
    import torch
    length = len(crops) - 5  # Match the upstream five-frame feature window count.
    visual = torch.from_numpy(crops.transpose(3, 0, 1, 2).copy()).float()
    lip_features = []
    with torch.inference_mode():
        for start in range(0, length, 8):
            batch = torch.stack([visual[:, i:i+5] for i in range(start, min(start+8, length))])
            lip_features.append(model.forward_lip(batch.to(device)).cpu().numpy())
    return np.concatenate(lip_features), audio_features(model, mfcc, pcm, length, device)


def audio_features(model, mfcc, pcm, length, device):
    import torch
    coefficients = torch.from_numpy(mfcc(pcm, 16000).T.copy()).float()
    output = []
    with torch.inference_mode():
        for start in range(0, length, 32):
            batch = torch.stack([coefficients[:, i*4:i*4+20] for i in range(start, min(start+32, length))])
            output.append(model.forward_aud(batch[:, None].to(device)).cpu().numpy())
    return np.concatenate(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--source', default='voice-video-soak-gpu-pcm')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label) or not re.fullmatch(r'voice-video-(soak|qualification)-[a-z0-9-]{1,32}', args.source):
        parser.error('Use a bounded synthetic benchmark source and short output label.')
    source = ROOT / 'generated/local-app/audit' / args.source
    output = ROOT / 'generated/local-app/audit' / ('lip-sync-' + args.label)
    if output.exists():
        parser.error('Output already exists; preserve it and use a fresh label.')
    qualification = json.loads((source / 'qualification.json').read_text())
    reviews = {r['id']: r for r in json.loads((source / 'frame-review.json').read_text())['reviews']}
    # First and last cycles, both body scales, three different synthetic phrases.
    cycles = sorted({row['cycle'] for row in qualification['results']})
    selected = [row for row in qualification['results'] if row['cycle'] in {cycles[0], cycles[-1]}
                and row['case'] in {'description', 'unsupported', 'conversation'} and 'job' in row]
    if not selected:
        raise ValueError('No matching retained synthetic speech fixtures.')
    preview_idle()
    model, mfcc, manifest = load_evaluator(args.device)
    output.mkdir()
    results = {'source': args.source, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'script_sha256': digest(Path(__file__)), 'evaluator': manifest, 'device': args.device,
               'scope': 'Offline diagnostic only. YuNet crop and interior-window scoring differ from upstream. 40ms estimate resolution. No perceptual, physical-audio or public eligibility acceptance.',
               'clips': [], 'skipped': []}
    started = time.perf_counter()
    try:
        for row in selected:
            preview_idle()
            job = row['job']
            if not re.fullmatch(r'[a-f0-9]{32}', job['id']) or len(job['chunks']) != 1:
                raise ValueError('Unexpected fixture identity or chunk count.')
            if not 2.2 <= job['chunks'][0]['duration_s'] <= 15:
                results['skipped'].append({'id': job['id'], 'case': row['case'], 'cycle': row['cycle'],
                                           'reason': 'Too short for 20 common interior windows over the full lag search.'})
                continue
            stem = job['id'] + '-0'
            video, wav = (source / 'retained-media' / (stem + suffix) for suffix in ['.mp4', '.wav'])
            crops, pcm, media = load_clip(video, wav, reviews[job['id']])
            lips, audio = features(model, mfcc, crops, pcm, args.device)
            radius = min(20, (len(lips)-20)//2)
            baseline = offset_score(lips, audio, radius)
            controls = []
            for delay in [-400, -200, 200, 400]:
                shifted = audio_features(model, mfcc, shift_audio(pcm, delay * 16), len(lips), args.device)
                score = offset_score(lips, shifted, radius)
                score.update(injected_delay_ms=delay, relative_error_ms=score['audio_delay_ms']-baseline['audio_delay_ms']-delay)
                controls.append(score)
            reversed_score = offset_score(lips, audio_features(model, mfcc, pcm[::-1].copy(), len(lips), args.device), radius)
            calibrated = all(abs(c['relative_error_ms']) <= 40 and not c['at_search_boundary'] for c in controls)
            item = {'id': job['id'], 'case': row['case'], 'cycle': row['cycle'], 'pose': job['prepared_pose'],
                    'media': media, 'baseline': baseline, 'shift_controls': controls, 'reversed_audio': reversed_score,
                    'search_radius_frames': radius,
                    'shift_controls_pass': calibrated,
                    'reverse_confidence_lower': reversed_score['confidence'] < baseline['confidence'],
                    'human_acceptance': False}
            results['clips'].append(item)
            print(json.dumps({k: item[k] for k in ['case', 'cycle', 'pose', 'shift_controls_pass', 'reverse_confidence_lower']} | {'audio_delay_ms': baseline['audio_delay_ms'], 'confidence': baseline['confidence']}), flush=True)
        results['complete'] = True
    finally:
        results['elapsed_s'] = time.perf_counter() - started
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
