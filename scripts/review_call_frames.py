"""Every-frame diagnostics for isolated neutral call benchmarks, not a quality certificate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]


def inspect_video(path):
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames, diagnostics = [], []
    detector = None
    try:
        if not 1 <= fps <= 60:
            raise ValueError('Invalid frame rate.')
        for index in range(1801):
            ok, frame = capture.read()
            if not ok:
                break
            if index == 1800 or frame.shape[0]*frame.shape[1] > 1920*1920:
                raise ValueError('Unexpected media size or length.')
            height, width = frame.shape[:2]
            if detector is None:
                detector = cv2.FaceDetectorYN.create(str(ROOT/'.cache/local-poc/yunet.onnx'), '', (width,height), .65,.3,5000)
            _, faces = detector.detect(frame)
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            delta = float(np.abs(frame.astype(np.float32)-frames[-1]).mean()) if frames else 0
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC)/1000
            if not np.isfinite(timestamp) or (diagnostics and timestamp <= diagnostics[-1]['time_s']):
                raise ValueError('Decoded timestamps are unavailable.')
            row = {'frame':index, 'time_s':timestamp, 'faces':0 if faces is None else len(faces),
                   'delta_mae':round(delta,3), 'luma':round(float(grey.mean()),3)}
            if faces is not None and len(faces) == 1:
                x,y,w,h = faces[0][:4]
                box = [max(0,int(x)),max(0,int(y)),min(width,int(x+w)),min(height,int(y+h))]
                crop = grey[box[1]:box[3],box[0]:box[2]]
                row.update(face_box=box,face_sharpness=round(float(cv2.Laplacian(crop,cv2.CV_64F).var()),3))
            diagnostics.append(row); frames.append(frame)
    finally:
        capture.release()
    if not frames:
        raise ValueError('No decoded frames.')
    deltas = [r['delta_mae'] for r in diagnostics[1:]]
    median = float(np.median(deltas)) if deltas else 0
    for row in diagnostics:
        row['flags'] = []
        if row['faces'] != 1: row['flags'].append('face_count')
        if row['delta_mae'] > max(12, median*5): row['flags'].append('abrupt_change')
        if row['luma'] < 5: row['flags'].append('dark_frame')
    steps = np.diff([row['time_s'] for row in diagnostics])
    step = float(np.median(steps)) if len(steps) else 1/fps
    summary = {'decoded_frames':len(frames),'fps':1/step,'container_average_fps':fps,
               'duration_s':diagnostics[-1]['time_s']-diagnostics[0]['time_s']+step,
               'flagged_frames':[r['frame'] for r in diagnostics if r['flags']],
               'max_adjacent_mae':max(deltas,default=0),'median_adjacent_mae':median}
    return frames, diagnostics, summary


def review_sheets(frames, diagnostics, folder, stem):
    """Every frame appears once, in sequence; review remains a human judgment."""
    for start in range(0,len(frames),20):
        sheet=Image.new('RGB',(1024,5*408),'#161616'); draw=ImageDraw.Draw(sheet)
        for offset,frame in enumerate(frames[start:start+20]):
            picture=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));picture.thumbnail((256,384))
            x,y=offset%4*256,offset//4*408
            sheet.paste(picture,(x,y));draw.text((x+4,y+387),f'{start+offset}: {diagnostics[start+offset]["time_s"]:.2f}s',fill='white')
        sheet.save(folder/f'{stem}-frames-{start:03}.jpg')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',choices=['wave','qualification','soak'],required=True)
    parser.add_argument('--label',default='')
    args=parser.parse_args()
    if args.label and not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):
        parser.error('Use a short lowercase label, digits and hyphens only.')
    folder=ROOT/'generated/local-app/audit'/('voice-video-'+args.trial+('-'+args.label if args.label else ''))
    jobs=([row['job'] for row in json.loads((folder/'qualification.json').read_text())['results'] if 'job' in row]
          if (folder/'qualification.json').exists() else json.loads((folder/'engine-results.json').read_text()))
    reviews=[]
    for job in jobs:
        for chunk in job['chunks']:
            name=chunk['audio'].rsplit('/',1)[-1]
            if not re.fullmatch(r'[a-f0-9]{32}-\d+\.wav',name):
                raise ValueError('Unexpected benchmark filename.')
            archive=folder/'retained-media'/name
            audio_path=archive if archive.exists() else folder/name
            video_path=audio_path.with_suffix('.mp4')
            if not video_path.exists():
                reviews.append({'id':job['id'],'chunk':chunk['index'],'state':job['state'],'media_missing':True})
                continue
            frames,diagnostics,summary=inspect_video(video_path)
            audio,rate=sf.read(audio_path,dtype='float32')
            summary.update(audio_seconds=len(audio)/rate,audio_rms=float(np.sqrt(np.mean(audio*audio))),
                           audio_peak=float(np.max(np.abs(audio))),audio_clipped_fraction=float(np.mean(np.abs(audio)>=.999)))
            review_sheets(frames, diagnostics, folder, video_path.stem)
            item={'id':job['id'],'action':job['action'],'chunk':chunk['index'],'summary':summary,'frames':diagnostics,
                  'video_sha256':hashlib.sha256(video_path.read_bytes()).hexdigest()}
            reviews.append(item)
            print(json.dumps({'action':job['action'],'id':job['id'],**summary}),flush=True)
    output={'scope':'Every decoded frame inspected for face count, luma and adjacent pixel change; every frame appears in ordered review sheets. These heuristics do not prove correct identity, anatomy, hand count, natural motion or phoneme alignment. Physical audio is not checked.',
            'reviews':reviews}
    (folder/'frame-review.json').write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__': main()
