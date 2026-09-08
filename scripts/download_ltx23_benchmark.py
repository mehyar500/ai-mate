"""Download two pinned official-workflow assets for a non-explicit LTX-2.3 benchmark.

About 39 GB of weights. Does not select them in the companion app. Weight licenses
are separate from ComfyUI's license; no public-deployment clearance is implied.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / '.cache/local-poc/ComfyUI/models'
FILES = [
    dict(repo='Lightricks/LTX-2.3-fp8', revision='1d756cd27fa11c0896c4dfee093cd1bf36c7f7a1',
         filename='ltx-2.3-22b-distilled-fp8.safetensors', folder='checkpoints', size=29531884062,
         sha256='d9646b6f2d5c42d337b23671634c43bfeece6989644f51b4a3aa088465ccd3b2'),
    dict(repo='Comfy-Org/ltx-2', revision='101c239b4b64dd1b45d645365339c56e0e7df4c3',
         filename='split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors', folder='text_encoders', size=9447702218,
         sha256='aaca463d11e6d8d2a4bdb0d6299214c15ef78a3f73e0ef8113d5a9d0219b3f6d'),
]


def download(spec):
    destination = MODELS/spec['folder']/Path(spec['filename']).name
    if not destination.exists():
        downloaded = Path(hf_hub_download(spec['repo'],spec['filename'],revision=spec['revision'],
                                         local_dir=MODELS/spec['folder'],token=False))
        if downloaded != destination:
            # Move only this exact downloaded file within the already-resolved model directory.
            assert downloaded.resolve().is_relative_to((MODELS/spec['folder']).resolve())
            downloaded.replace(destination)
    if destination.stat().st_size != spec['size']:
        raise RuntimeError('Incomplete model: '+destination.name)
    with destination.open('rb') as source:
        checksum=hashlib.file_digest(source,'sha256').hexdigest()
    if checksum != spec['sha256']:
        raise RuntimeError('Model checksum mismatch: '+destination.name)
    print(json.dumps({'verified':destination.name,'size':spec['size'],'sha256':checksum}),flush=True)


if __name__ == '__main__':
    if shutil.disk_usage(ROOT).free < 45_000_000_000:
        raise SystemExit('At least 45 GB of free workspace disk space is required.')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, FILES))
