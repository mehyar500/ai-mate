"""Prepare an approach/return pair or wave candidate for local review.

Run between calls; restart the app only after reviewing the prepared outputs.
The generated manifest is intentionally unreviewed and cannot enable itself.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import cv2

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--duration',type=float,default=3.0)
    parser.add_argument('--action',choices=['approach','wave'],default='approach')
    args=parser.parse_args()
    source=args.source.resolve()
    allowed=[ROOT/'.cache/local-poc/ComfyUI/output/motion',ROOT/'generated/local-app/audit']
    if source.parent not in [p.resolve() for p in allowed] or source.suffix!='.mp4':
        parser.error('Use a reviewed local benchmark MP4.')
    if not source.is_file() or source.stat().st_size>40_000_000 or not 1<=args.duration<=4.5:
        parser.error('Use a bounded clip and a 1–4.5 second transition.')
    folder=ROOT/'generated/local-app'
    if args.action == 'wave':
        target=folder/'performance-wave.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-t',str(args.duration),
                        '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(target)],check=True,timeout=30)
        manifest={'version':1,'reviewed':False,'model':'LTX-2.3-22B-distilled-FP8',
                  'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                            for name in ['fullbody.png','performance-wave.mp4']}}
        record=folder/'performance-wave.json'
        record.write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'manifest':str(record),'requires_output_review':True}))
        return
    forward=folder/'performance-closer.mp4';backward=folder/'performance-farther.mp4'
    encode=['-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart']
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-t',str(args.duration),*encode,str(forward)],check=True,timeout=30)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(forward),'-vf','reverse',*encode,str(backward)],check=True,timeout=30)
    capture=cv2.VideoCapture(str(forward));last=None
    try:
        for _ in range(300):
            ok,frame=capture.read()
            if not ok:break
            last=frame
    finally:
        capture.release()
    if last is None or last.shape[:2]!=(576,384):
        raise ValueError('The transition must decode at 384x576.')
    reference=folder/'performance-near.png'
    if not cv2.imwrite(str(reference),last):
        raise OSError('Could not write the close-view reference.')
    names=['fullbody.png','performance-near.png','performance-closer.mp4','performance-farther.mp4']
    manifest={'version':1,'reviewed':False,'model':'LTX-2.3-22B-distilled-FP8',
              'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'duration_s':args.duration,'return_method':'reversed_prepared_approach',
              'sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names}}
    (folder/'performance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'reference':str(reference),'manifest':str(folder/'performance.json'),'requires_output_review':True}))


if __name__=='__main__':
    main()
