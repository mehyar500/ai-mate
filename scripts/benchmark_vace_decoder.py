"""Validate incremental TAEW2.1 decoding of retained, neutral VACE test latents.

This measures decoding only. Already generated latents cannot prove streaming
generation, action responsiveness, speech synchronization or call performance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('latents', type=Path)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    source = args.latents.resolve()
    audit = (ROOT / 'generated/local-app/audit').resolve()
    if not source.is_relative_to(audit) or source.suffix != '.safetensors' or not 0 < source.stat().st_size < 20_000_000:
        parser.error('Use bounded retained VACE test latents inside the audit folder.')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', args.label):
        parser.error('Use a fresh lowercase experiment label.')
    output = audit / ('vace-decoder-' + args.label)
    output.mkdir(exist_ok=False)
    record = {'complete': False, 'source': source.relative_to(ROOT).as_posix(),
              'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'scope': 'Decoder only on already generated latents; no live generation or audio',
              'api_cost_usd': 0, 'live_app_selected': False}
    try:
        import torch
        from safetensors.torch import load_file
        from scripts.vace_tiny_vae import TinyWanVAE
        torch.set_num_threads(8)
        torch.set_grad_enabled(False)
        tensors = load_file(str(source))
        if set(tensors) != {'latents'}:
            raise ValueError('Expected the VACE benchmark latent file.')
        # The first latent is the VACE reference prefix, not a video frame.
        latent = tensors['latents'][:, 1:].to('cuda')
        decoder = TinyWanVAE('cuda')
        torch.cuda.synchronize()
        began = time.perf_counter()
        parallel = decoder.decode([latent])[0]
        torch.cuda.synchronize()
        record['batch_decode_s'] = time.perf_counter() - began
        record['shape'] = list(parallel.shape)
        record['batch_agreement_limits_0_1'] = {'mean': .25 / 255, 'maximum': 2 / 255}
        record['runs'] = []
        previous = None
        for _ in range(3):
            began = time.perf_counter()
            frames, arrival = [], []
            for frame in decoder.decode_stream(latent[:, i:i + 1] for i in range(latent.shape[1])):
                torch.cuda.synchronize()
                arrival.append(time.perf_counter() - began)
                frames.append(frame)
            video = torch.stack(frames, dim=1)
            if video.shape != parallel.shape or not torch.isfinite(video).all():
                raise ValueError('Streaming decode lost frames or produced invalid pixels.')
            record['runs'].append({'first_frame_s': arrival[0], 'total_s': arrival[-1],
                                   'arrival_s': arrival,
                                   'batch_pixel_mae_0_1': float((video - parallel).abs().mean() / 2),
                                   'batch_pixel_max_error_0_1': float((video - parallel).abs().max() / 2),
                                   'reset_exact': None if previous is None else bool(torch.equal(video, previous))})
            last = record['runs'][-1]
            if last['batch_pixel_mae_0_1'] > .25 / 255 or last['batch_pixel_max_error_0_1'] > 2 / 255:
                raise ValueError('Streaming versus batch difference exceeds the recorded numerical limits.')
            previous = video
        # An interrupted stream must not contaminate a subsequent call.
        interrupted = decoder.decode_stream([latent[:, :1]])
        next(interrupted)
        interrupted.close()
        restarted = torch.stack(list(decoder.decode_stream([latent])), dim=1)
        record['cancel_restart_exact'] = bool(torch.equal(restarted, previous))
        if not record['cancel_restart_exact'] or not all(row['reset_exact'] for row in record['runs'][1:]):
            raise ValueError('Decoder state leaked between streams.')
        record['complete'] = True
    except Exception as error:
        record['error_type'], record['error'] = type(error).__name__, str(error)[:1000]
        raise
    finally:
        (output / 'benchmark.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record))


if __name__ == '__main__':
    main()
