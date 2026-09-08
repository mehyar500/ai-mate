"""Compare idle footage using background optical flow and eye contact sheets.

Metrics aid review; they do not prove a natural blink or acceptable image quality.
No assets are edited or promoted by this script.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    roots = [ROOT/'generated/local-app', ROOT/'.cache/local-poc/ComfyUI/output/motion']
    if source.suffix != '.mp4' or not any(source.is_relative_to(p.resolve()) for p in roots):
        parser.error('Use a local app or benchmark MP4.')
    cv2.setNumThreads(2)
    capture = cv2.VideoCapture(str(source))
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = []
    try:
        for _ in range(482):
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[:2] != (576, 384):
                parser.error('Use a 384x576 comparison clip.')
            frames.append(frame)
    finally:
        capture.release()
    if not 2 <= len(frames) <= 481 or not 1 <= fps <= 60:
        parser.error('Use a valid short clip.')
    detector = cv2.FaceDetectorYN.create(str(ROOT/'.cache/local-poc/yunet.onnx'), '', (384,576), .65, .3, 5000)
    _, faces = detector.detect(frames[0])
    if faces is None or len(faces) != 1:
        parser.error('The starting frame needs one visible face.')
    x,y,w,h = faces[0][:4]
    # Fixed region makes shifts and asymmetric eyelids visible during review.
    box = (max(0,int(x-.15*w)),max(0,int(y-.15*h)),min(384,int(x+1.15*w)),min(576,int(y+.85*h)))
    # Include both endpoints even when a clip has 97–127 frames; truncating a
    # stride-one list hid the final second and the loop seam from review.
    indices = np.linspace(0,len(frames)-1,min(96,len(frames))).round().astype(int)
    cols = 12
    sheet = Image.new('RGB',(cols*128,((len(indices)+cols-1)//cols)*106),'#242424')
    for k,index in enumerate(indices):
        x1,y1,x2,y2=box
        crop = Image.fromarray(cv2.cvtColor(frames[index][y1:y2,x1:x2],cv2.COLOR_BGR2RGB))
        crop.thumbnail((124,84))
        scale=min(124/crop.width,84/crop.height)
        crop=crop.resize((round(crop.width*scale),round(crop.height*scale)))
        sx,sy=(k%cols)*128,(k//cols)*106
        sheet.paste(crop,(sx+(128-crop.width)//2,sy))
        ImageDraw.Draw(sheet).text((sx+4,sy+87),f'{index/fps:.2f}s',fill='white')
    # Side strips exclude the person for these fixed-camera references.
    mask=np.zeros((576,384),dtype=bool)
    mask[30:500,:70]=True;mask[30:500,315:]=True
    magnitudes=[]
    previous=cv2.cvtColor(frames[0],cv2.COLOR_BGR2GRAY)
    for frame in frames[1:]:
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        flow=cv2.calcOpticalFlowFarneback(previous,gray,None,.5,3,15,3,5,1.2,0)
        magnitudes.append(np.sqrt((flow**2).sum(axis=2))[mask])
        previous=gray
    values=np.concatenate(magnitudes)*fps
    out=ROOT/'generated/local-app/audit'/f'{source.stem}-eyes.jpg'
    sheet.save(out)
    result={'frames':len(frames),'fps':fps,'duration_s':len(frames)/fps,
            'background_mean_px_s':float(np.mean(values)),
            'background_p95_px_s':float(np.percentile(values,95)),
            'eye_contact_sheet':str(out),'blink_review':'manual, not inferred from flow'}
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
