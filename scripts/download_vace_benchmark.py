"""Fetch pinned original VACE weights; reuse hash-verified local VAE/text assets."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import functools
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_longlive2_benchmark import download

CACHE = ROOT / '.cache/local-poc/vace-models'


def download_tiny(manifest):
    """Bound and verify the optional source/weights before executing any code."""
    spec = manifest['tiny_vae_experiment']
    rows = spec['files']
    if sum(row['size'] for row in rows) > 30_000_000:
        raise ValueError('Tiny VAE assets exceed the 30MB experiment cap.')
    cache = (ROOT / '.cache/local-poc/taehv').resolve()
    prefix = 'https://raw.githubusercontent.com/madebyollin/taehv/' + spec['source_revision'] + '/'
    if shutil.disk_usage(ROOT).free < 100_000_000:
        raise RuntimeError('Insufficient space for tiny VAE assets.')
    for row in rows:
        path = (ROOT / row['path']).resolve()
        if not path.is_relative_to(cache) or not row['source_url'].startswith(prefix):
            raise ValueError('Unexpected tiny VAE source or destination.')
        if not path.exists():
            with urllib.request.urlopen(row['source_url'], timeout=60) as response:
                data = response.read(row['size'] + 1)
            if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Unverified tiny VAE download: ' + path.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as stream:
                partial = Path(stream.name)
                stream.write(data)
            try:
                partial.replace(path)
            finally:
                partial.unlink(missing_ok=True)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if path.stat().st_size != row['size'] or digest != row['sha256']:
            raise ValueError('Unverified cached tiny VAE asset: ' + path.name)
        print(json.dumps({'verified': path.name, 'bytes': row['size']}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--rcm-only', action='store_true', help='Fetch optional accelerated generator, not the VACE baseline.')
    selection.add_argument('--tiny-vae-only', action='store_true', help='Fetch the pinned MIT approximate VAE source and weights.')
    selection.add_argument('--causal-only', action='store_true', help='Fetch the optional one-frame causal rCM generator.')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'config/vace-benchmark.json').read_text(encoding='utf-8'))
    if args.tiny_vae_only:
        download_tiny(manifest)
        return
    files = (manifest['causal_rcm_experiment']['files'] if args.causal_only else
             manifest['rcm_experiment']['files'] if args.rcm_only else manifest['files'])
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
