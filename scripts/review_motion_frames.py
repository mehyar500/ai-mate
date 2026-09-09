"""Inspect every frame of a bounded local motion source before selecting it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.review_call_frames import inspect_video, review_sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--label',default='')
    args = parser.parse_args()
    source = args.source.resolve()
    roots = [ROOT/'generated/local-app', ROOT/'.cache/local-poc/ComfyUI/output/motion']
    if source.suffix != '.mp4' or not any(source.is_relative_to(p.resolve()) for p in roots):
        parser.error('Use a local app or benchmark MP4.')
    if not 0 < source.stat().st_size <= 40_000_000:
        parser.error('Use a short bounded motion source.')
    if args.label and not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):
        parser.error('Use a short lowercase review label.')
    folder = ROOT/'generated/local-app/audit'/('frames-'+source.stem+('-'+args.label if args.label else ''))
    folder.mkdir(exist_ok=False)
    frames, diagnostics, summary = inspect_video(source)
    review_sheets(frames, diagnostics, folder, source.stem)
    result = {'source':source.relative_to(ROOT).as_posix(),
              'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'summary':summary,'frames':diagnostics,
              'scope':'Every decoded frame; heuristics do not certify anatomy, identity, motion or lip sync. Ordered sheets need visual review.'}
    (folder/'review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'folder':str(folder),**summary}))


if __name__ == '__main__':
    main()
