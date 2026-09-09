"""Download hash-pinned LongLive 2.0 motion experiment weights, never select them."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/local-poc/longlive2-models'


def download(spec):
    folder = (CACHE / spec['folder']).resolve()
    destination = (folder / spec['filename']).resolve()
    if not destination.is_relative_to(CACHE.resolve()):
        raise ValueError('Download must remain inside the experiment cache.')
    if not destination.exists():
        path = Path(hf_hub_download(spec['repo'], spec['filename'], revision=spec['revision'],
                                    local_dir=folder, token=False))
        if path.resolve() != destination:
            raise ValueError('Unexpected download destination.')
    if destination.stat().st_size != spec['size']:
        raise ValueError('Unexpected file size: ' + destination.name)
    with destination.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != spec['sha256']:
        raise ValueError('Checksum mismatch: ' + destination.name)
    print(json.dumps({'verified': spec['filename'], 'bytes': spec['size']}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--light-vae-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'config/longlive2-benchmark.json').read_text(encoding='utf-8'))
    files = manifest.get('optional_files', []) if args.light_vae_only else manifest['files']
    if sum(row['size'] for row in files) > 25_000_000_000:
        raise ValueError('Selected downloads exceed the 25 GB cap.')
    missing = sum(row['size'] for row in files
                  if not (CACHE / row['folder'] / row['filename']).exists())
    if shutil.disk_usage(ROOT).free < missing + 5_000_000_000:
        raise RuntimeError('Insufficient free space for the pinned experiment.')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, files))


if __name__ == '__main__':
    main()
