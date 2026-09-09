"""Download verified public assets for the isolated neutral Supertonic comparison."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'.cache/local-poc/supertonic3'
CONFIG=ROOT/'config/supertonic-benchmark.json'


def verified_files():
    spec=json.loads(CONFIG.read_text(encoding='utf-8'))
    for item in spec['files']:
        target=(FOLDER/item['path']).resolve()
        if not target.is_relative_to(FOLDER.resolve()):raise ValueError('Unexpected artifact path.')
        if not target.is_file() or target.stat().st_size!=item['bytes']:
            raise ValueError('Run download_supertonic_benchmark.py to install the pinned assets.')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Supertonic artifact differs from its recorded hash.')
    return spec


def main():
    spec=json.loads(CONFIG.read_text(encoding='utf-8'))
    FOLDER.mkdir(parents=True,exist_ok=True)
    for item in spec['files']:
        target=(FOLDER/item['path']).resolve()
        if not target.is_relative_to(FOLDER.resolve()):raise ValueError('Unexpected artifact path.')
        if target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True);partial=target.with_suffix(target.suffix+'.part')
        digest=hashlib.sha256();size=0
        try:
            with urllib.request.urlopen(item['url'],timeout=60) as response,partial.open('wb') as output:
                while chunk:=response.read(1024*1024):
                    size+=len(chunk)
                    if size>item['bytes']:raise ValueError('Artifact exceeds its pinned size.')
                    digest.update(chunk);output.write(chunk)
            if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise ValueError('Downloaded artifact hash/size mismatch.')
            partial.replace(target)
            print(json.dumps({'verified':item['path'],'bytes':size}),flush=True)
        finally:
            if partial.exists():partial.unlink()
    verified_files();print(json.dumps({'all_files_verified':True,'selected_in_app':False}))


if __name__=='__main__':main()
