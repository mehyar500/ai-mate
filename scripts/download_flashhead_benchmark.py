"""Fetch pinned FlashHead Lite research weights (about 8.2 GB), never select them.

Top-level Apache licensing does not settle each bundled VAE/voice/asset right.
This is for the private non-explicit benchmark, not deployment clearance.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import hf_hub_download

ROOT=Path(__file__).resolve().parents[1]
MODEL_REVISION='59119b6c681230c3eeee157e224ae1941746711e'
WAV_REVISION='22aad52d435eb6dbaf354bdad9b0da84ce7d6156'
MODELS=ROOT/'.cache/local-poc/flashhead-models'
FILES=[
    ('Soul-AILab/SoulX-FlashHead-1_3B',MODEL_REVISION,'Model_Lite/config.json',357,None),
    ('Soul-AILab/SoulX-FlashHead-1_3B',MODEL_REVISION,'Model_Lite/diffusion_pytorch_model.safetensors',6107542048,'aaf1cde6e80ca23f740aae236c47954249f65b151db133cc0f77d3a138ccdf6e'),
    ('Soul-AILab/SoulX-FlashHead-1_3B',MODEL_REVISION,'VAE_LTX/config.json',501,None),
    ('Soul-AILab/SoulX-FlashHead-1_3B',MODEL_REVISION,'VAE_LTX/diffusion_pytorch_model.safetensors',1676798532,'265ca87cb5dff5e37f924286e957324e282fe7710a952a7dafc0df43883e2010'),
    ('Soul-AILab/SoulX-FlashHead-1_3B',MODEL_REVISION,'README.md',8325,None),
    ('facebook/wav2vec2-base-960h',WAV_REVISION,'config.json',1596,None),
    ('facebook/wav2vec2-base-960h',WAV_REVISION,'preprocessor_config.json',159,None),
    ('facebook/wav2vec2-base-960h',WAV_REVISION,'model.safetensors',377607901,'8aa76ab2243c81747a1f832954586bc566090c83a0ac167df6f31f0fa917d74a'),
]


def download(spec):
    repo,revision,name,size,expected=spec
    folder=MODELS/('wav2vec2' if repo.startswith('facebook/') else 'flashhead')
    path=Path(hf_hub_download(repo,name,revision=revision,local_dir=folder,token=False))
    if path.stat().st_size!=size:
        raise RuntimeError('Incomplete model file: '+name)
    with path.open('rb') as file:
        digest=hashlib.file_digest(file,'sha256').hexdigest()
    if expected and digest!=expected:
        raise RuntimeError('Checksum mismatch: '+name)
    print(json.dumps({'repo':repo,'file':name,'sha256':digest,'verified_bytes':size}),flush=True)


if __name__=='__main__':
    if shutil.disk_usage(ROOT).free<10_000_000_000:
        raise SystemExit('At least 10 GB of free disk is needed.')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download,FILES))
