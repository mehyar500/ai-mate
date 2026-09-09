"""Fetch the pinned offline evaluator into ignored cache, without changing app packages."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/local-poc/syncnet-evaluator'


def verify(data, expected, name):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('SHA-256 mismatch: ' + name)


def main():
    manifest = json.loads((ROOT / 'config/syncnet-evaluator.json').read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in manifest['downloads'].items():
        if Path(name).name != name or urlparse(url).scheme != 'https':
            raise ValueError('Expected a cache filename and HTTPS source.')
        path = CACHE / name
        if path.exists():
            verify(path.read_bytes(), manifest['download_sha256'][name], name)
            continue
        limit = 60_000_000 if name == 'syncnet_v2.model' else 50_000
        with urllib.request.urlopen(url, timeout=60) as response:
            if urlparse(response.url).scheme != 'https':
                raise ValueError('Insecure download redirect.')
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Download exceeds size cap.')
        verify(data, manifest['download_sha256'][name], name)
        # No partial file is installed when the network or verification fails.
        with path.open('xb') as destination:
            destination.write(data)
        print(json.dumps({'downloaded': name, 'bytes': len(data)}), flush=True)
    archive = CACHE / 'python_speech_features-0.6.tar.gz'
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes()), mode='r:gz') as tar:
        # Read only three known Python files. No extractall, setup.py, shell
        # installer, S3FD model or unrelated sample footage is executed/fetched.
        for relative, expected in manifest['runtime_sha256'].items():
            if not relative.startswith('python_speech_features/'):
                continue
            path = (CACHE / relative).resolve()
            if not path.is_relative_to(CACHE.resolve()):
                raise ValueError('Unexpected archive destination.')
            member = tar.getmember('python_speech_features-0.6/' + relative)
            if not member.isfile() or member.size > 20_000:
                raise ValueError('Unexpected archive member.')
            data = tar.extractfile(member).read()
            verify(data, expected, relative)
            path.parent.mkdir(exist_ok=True)
            if path.exists():
                verify(path.read_bytes(), expected, relative)
            else:
                with path.open('xb') as destination:
                    destination.write(data)
    print('Pinned offline evaluator verified. The live app environment was not changed.')


if __name__ == '__main__':
    main()
