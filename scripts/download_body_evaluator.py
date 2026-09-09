"""Fetch a pinned CPU-only body diagnostic into ignored cache; no app installation."""
import hashlib
import json
from pathlib import Path
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/local-poc/body-evaluator'


def main():
    manifest = json.loads((ROOT/'config/body-evaluator.json').read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, spec in manifest['files'].items():
        if Path(name).name != name or not 0 < spec['bytes'] <= 15_000_000:
            raise ValueError('Unexpected evaluator asset.')
        parsed = urlparse(spec['url'])
        if parsed.scheme != 'https' or parsed.hostname not in {'raw.githubusercontent.com','media.githubusercontent.com'}:
            raise ValueError('Use the pinned upstream HTTPS source.')
        destination = CACHE/name
        if destination.resolve().parent != CACHE.resolve():
            raise ValueError('Evaluator asset escapes its cache.')
        if destination.exists():
            if destination.stat().st_size != spec['bytes']:
                raise ValueError('Cached evaluator asset has the wrong size: '+name)
            payload = destination.read_bytes()
        else:
            with urllib.request.urlopen(spec['url'], timeout=30) as response:
                final = urlparse(response.url)
                if final.scheme != 'https' or final.hostname != parsed.hostname:
                    raise ValueError('Unexpected evaluator download redirect.')
                payload = response.read(spec['bytes']+1)
        if len(payload) != spec['bytes'] or hashlib.sha256(payload).hexdigest() != spec['sha256']:
            raise ValueError('Evaluator size or hash mismatch: '+name)
        if not destination.exists():
            with destination.open('xb') as output:
                output.write(payload)
        print(json.dumps({'verified':name,'bytes':len(payload)}))


if __name__ == '__main__':
    main()
