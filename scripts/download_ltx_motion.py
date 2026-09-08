"""Pinned, small LTX image-to-video checkpoint and FP8 text encoder for ComfyUI."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1] / '.cache/local-poc/ComfyUI/models'
FILES = [
    ('Lightricks/LTX-Video', '8984fa25007f376c1a299016d0957a37a2f797bb',
     'ltxv-2b-0.9.8-distilled-fp8.safetensors', 'checkpoints'),
    ('comfyanonymous/flux_text_encoders', '6af2a98e3f615bdfa612fbd85da93d1ed5f69ef5',
     't5xxl_fp8_e4m3fn.safetensors', 'text_encoders'),
]


def download(spec):
    repo, revision, filename, folder = spec
    result = hf_hub_download(repo, filename, revision=revision, local_dir=ROOT / folder)
    print(f'Complete: {filename} ({Path(result).stat().st_size} bytes)', flush=True)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, FILES))
