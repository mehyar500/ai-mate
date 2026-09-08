"""Extract bounded contact sheets for visual review; metrics do not certify quality."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    args=parser.parse_args()
    source=args.source.resolve()
    roots=[ROOT/'generated/local-app',ROOT/'.cache/local-poc/ComfyUI/output/motion']
    if not any(source.is_relative_to(p.resolve()) for p in roots) or source.suffix!='.mp4':
        parser.error('Use a private app/benchmark video.')
    capture=cv2.VideoCapture(str(source))
    fps=capture.get(cv2.CAP_PROP_FPS)
    count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not 1<=fps<=60 or not 2<=count<=1800:
        capture.release();parser.error('Missing video or unsupported length/frame rate.')
    sheet=Image.new('RGB',(1536,1212),'#222222')
    endpoints=[]
    try:
        for k in range(8):
            index=round(k*(count-1)/7)
            capture.set(cv2.CAP_PROP_POS_FRAMES,index)
            ok,frame=capture.read()
            if not ok:raise ValueError('A requested frame could not be decoded.')
            if k in {0,7}:endpoints.append(frame.astype(np.float32))
            picture=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            picture.thumbnail((384,576))
            x,y=k%4*384,k//4*606
            sheet.paste(picture,(x+(384-picture.width)//2,y))
            ImageDraw.Draw(sheet).text((x+8,y+579),f'{index/fps:.2f}s',fill='white')
    finally:
        capture.release()
    folder=ROOT/'generated/local-app/audit';folder.mkdir(exist_ok=True)
    output=folder/(source.stem+'-review.jpg');sheet.save(output)
    print(json.dumps({'contact_sheet':str(output),'frames':count,'fps':fps,
                      'endpoint_mae':float(np.mean(np.abs(endpoints[0]-endpoints[1]))),
                      'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))


if __name__=='__main__':
    main()
