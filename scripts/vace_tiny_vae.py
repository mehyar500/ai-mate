"""Wan list/CTHW conventions around the pinned MIT TAEW2.1 implementation.

TAEW2.1 directly uses diffusion-model latents: no additional mean/std scaling.
Encoder and decoder are approximations, not numerically equivalent to Wan VAE.
"""
import importlib.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TinyWanVAE:
    def __init__(self, device):
        import torch
        folder = ROOT / '.cache/local-poc/taehv'
        manifest = json.loads((ROOT / 'config/vace-benchmark.json').read_text(encoding='utf-8'))
        for row in manifest['tiny_vae_experiment']['files']:
            path = ROOT / row['path']
            if path.stat().st_size != row['size'] or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Unverified tiny VAE asset: ' + path.name)
        spec = importlib.util.spec_from_file_location('ai_mate_taew21', folder / 'taehv.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.model = module.TAEHV(folder / 'safetensors/taew2_1.safetensors').eval().requires_grad_(False)
        self.model.to(device=device, dtype=torch.float16)
        self.device = device
        self.streaming_type = module.StreamingTAEHV

    def _as_ntchw(self, value, channels):
        import torch
        if (value.ndim != 4 or value.shape[0] != channels or not value.numel()
                or not value.is_floating_point() or not torch.isfinite(value).all()):
            raise ValueError(f'Expected finite, nonempty {channels}-channel floating CTHW input.')
        return value.permute(1, 0, 2, 3).unsqueeze(0).to(device=self.device, dtype=torch.float16)

    def encode(self, videos):
        import torch
        result = []
        for video in videos:
            rgb = (self._as_ntchw(video, 3) + 1) * .5
            with torch.inference_mode(), torch.autocast('cuda', enabled=False):
                encoded = self.model.encode_video(rgb, parallel=True, show_progress_bar=False)
            result.append(encoded[0].permute(1, 0, 2, 3).float())
        return result

    def decode(self, latents):
        import torch
        result = []
        for latent in latents:
            latent = self._as_ntchw(latent, 16)
            with torch.inference_mode(), torch.autocast('cuda', enabled=False):
                decoded = self.model.decode_video(latent, parallel=True, show_progress_bar=False)
            result.append(decoded[0].permute(1, 0, 2, 3).float() * 2 - 1)
        return result

    def decode_stream(self, chunks):
        """Yield CHW frames with one fresh causal state for this stream."""
        import torch
        stream = self.streaming_type(self.model)
        for chunk in chunks:
            value = self._as_ntchw(chunk, 16)
            with torch.inference_mode(), torch.autocast('cuda', enabled=False):
                frame = stream.decode(value)
            while frame is not None:
                # Never suspend inside a thread-local inference/autocast context:
                # callers must retain their own mode between yielded frames.
                yield frame[0, 0].float() * 2 - 1
                with torch.inference_mode(), torch.autocast('cuda', enabled=False):
                    frame = stream.decode()
