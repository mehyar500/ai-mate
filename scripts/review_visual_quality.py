"""Extract aligned face crops for manual review; not an automatic quality score."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'generated/local-app/audit/visual-quality'


def frame_at(path, seconds):
    capture = cv2.VideoCapture(str(path))
    try:
        capture.set(cv2.CAP_PROP_POS_MSEC, seconds*1000)
        ok, frame = capture.read()
        if not ok:
            raise ValueError('Missing synthetic comparison frame.')
        return frame
    finally:
        capture.release()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion',action='store_true')
    args=parser.parse_args()
    folder=ROOT/'generated/local-app/audit/visual-quality-motion' if args.motion else FOLDER
    sources=[('approach','performance-closer.mp4'),('return','performance-farther.mp4')] if args.motion else [('near','idle-near.mp4'),('body','idle-fullbody.mp4')]
    labels=['source','legacy','higher'] if args.motion else ['source','legacy','aligned','higher','highest']
    for scene, source in sources:
        sheet = np.full((len(labels)*264, 3*256, 3), 24, np.uint8)
        for row, label in enumerate(labels):
            for col, seconds in enumerate([.65, 1.35, 2.15]):
                original = frame_at(ROOT/'generated/local-app'/source, seconds)
                frame = original if label == 'source' else frame_at(folder/(scene+'-'+label+'.mp4'), seconds)
                detector = cv2.FaceDetectorYN.create(str(ROOT/'.cache/local-poc/yunet.onnx'), '',
                                                     (original.shape[1], original.shape[0]), .65, .3, 5000)
                _, faces = detector.detect(original)
                if faces is None or len(faces) != 1:
                    raise ValueError('No single source face for comparison.')
                x,y,w,h = faces[0][:4]
                x1,y1=max(0,int(x-.2*w)),max(0,int(y-.15*h))
                x2,y2=min(frame.shape[1],int(x+1.2*w)),min(frame.shape[0],int(y+1.15*h))
                crop = cv2.resize(frame[y1:y2,x1:x2],(256,236),interpolation=cv2.INTER_LINEAR)
                sheet[row*264+28:(row+1)*264,col*256:(col+1)*256]=crop
                cv2.putText(sheet,f'{label} {seconds:.2f}s',(col*256+8,row*264+19),
                            cv2.FONT_HERSHEY_SIMPLEX,.48,(245,245,245),1,cv2.LINE_AA)
        cv2.imwrite(str(folder/(scene+'-contact.jpg')),sheet)
    print(json.dumps({'contacts':[str(folder/(s+'-contact.jpg')) for s,_ in sources]}))


if __name__ == '__main__':
    main()
