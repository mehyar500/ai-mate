"""Fetch pinned original VACE weights; reuse hash-verified local VAE/text assets."""
from concurrent.futures import ThreadPoolExecutor
import functools
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_longlive2_benchmark import download

CACHE = ROOT / '.cache/local-poc/vace-models'


def main():
    manifest = json.loads((ROOT / 'config/vace-benchmark.json').read_text(encoding='utf-8'))
    files = manifest['files']
    if sum(row['size'] for row in files) > 8_000_000_000:
        raise ValueError('VACE download exceeds the 8GB experiment cap.')
    for row in manifest['reused_files']:
        path = (ROOT / row['path']).resolve()
        if not path.is_relative_to((ROOT / '.cache').resolve()):
            raise ValueError('Reused assets must stay inside the model cache.')
        if not path.is_file() or path.stat().st_size != row['size']:
            raise ValueError('Missing reused asset: ' + path.name)
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != row['sha256']:
                raise ValueError('Unverified reused asset: ' + path.name)
        print(json.dumps({'reused_verified': path.name, 'bytes': row['size']}), flush=True)
    missing = sum(row['size'] for row in files if not (CACHE / row['folder'] / row['filename']).exists())
    if shutil.disk_usage(ROOT).free < missing + 5_000_000_000:
        raise RuntimeError('Insufficient free space for VACE experiment.')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(functools.partial(download, cache=CACHE), files))


if __name__ == '__main__':
    main()
