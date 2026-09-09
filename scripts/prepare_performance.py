"""Prepare an approach/return pair or wave candidate for local review.

Run between calls; restart the app only after reviewing the prepared outputs.
The generated manifest is intentionally unreviewed and cannot enable itself.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import cv2

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--duration',type=float,default=3.0)
    parser.add_argument('--action',choices=['approach','wave'],default='approach')
    parser.add_argument('--pose',choices=['base','near'],default='base',help='Starting and ending pose for a wave.')
    parser.add_argument('--candidate-label',help='Prepare a new isolated bundle under audit; preserve active assets.')
    args=parser.parse_args()
    if args.pose == 'near' and (args.action != 'wave' or not args.candidate_label):
        parser.error('A near-view wave requires --action wave and an isolated --candidate-label.')
    source=args.source.resolve()
    allowed=[ROOT/'.cache/local-poc/ComfyUI/output/motion',ROOT/'generated/local-app/audit']
    if source.parent not in [p.resolve() for p in allowed] or source.suffix!='.mp4':
        parser.error('Use a reviewed local benchmark MP4.')
    if not source.is_file() or source.stat().st_size>40_000_000 or not 1<=args.duration<=4.5:
        parser.error('Use a bounded clip and a 1–4.5 second transition.')
    active=ROOT/'generated/local-app'
    folder=active
    if args.candidate_label:
        if not re.fullmatch(r'[a-z0-9-]{1,32}',args.candidate_label):
            parser.error('Use a short lowercase candidate label.')
        folder=active/'audit'/('performance-'+args.candidate_label)
        folder.mkdir(exist_ok=False)
        for name in ['fullbody.png','idle-fullbody.mp4','idle-fullbody.json',
                     'performance-wave.mp4','performance-wave.json']:
            if (active/name).is_file():
                shutil.copyfile(active/name,folder/name)
        if args.action == 'wave':
            for name in ['performance.json','performance-near.png','performance-closer.mp4',
                         'performance-farther.mp4','idle-near.mp4','idle-near.json']:
                if (active/name).is_file():
                    shutil.copyfile(active/name,folder/name)
    if args.action == 'wave':
        stem='performance-wave' if args.pose=='base' else 'performance-near-wave'
        reference='fullbody.png' if args.pose=='base' else 'performance-near.png'
        if not (folder/reference).is_file():
            parser.error('The matching reviewed pose reference is required.')
        target=folder/(stem+'.mp4')
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-t',str(args.duration),
                        '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(target)],check=True,timeout=30)
        manifest={'version':1,'reviewed':False,'pose':args.pose,'model':'LTX-2.3-22B-distilled-FP8',
                  'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                            for name in [reference,target.name]}}
        record=folder/(stem+'.json')
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
