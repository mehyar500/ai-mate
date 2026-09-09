"""Offline body-landmark diagnostics for retained neutral call recordings.

Every frame is evaluated. A fixed-skeleton model cannot count extra limbs or
certify anatomy, identity, consent or age; flags require visual inspection.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import socket
import time

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'.cache/local-poc/body-evaluator'
# MediaPipe: left/right shoulders, elbows, wrists, hips, knees and ankles.
JOINTS = (11,12,13,14,15,16,23,24,25,26,27,28)
BONES = ((11,13),(13,15),(12,14),(14,16),(23,25),(25,27),(24,26),(26,28))


def landmark_metrics(points, width, height, previous=None):
    """Return estimates, uncertainty and discontinuities without declaring anatomy valid."""
    if len(points) < 33 or min(width,height) <= 0:
        raise ValueError('Expected a MediaPipe pose and positive frame size.')
    if any(len(p) < 5 or not all(math.isfinite(float(v)) for v in p[:5]) for p in points[:33]):
        raise ValueError('Non-finite or malformed pose.')
    visible = {i for i in JOINTS if points[i][3] >= .5 and points[i][4] >= .5}
    inside = {i for i in visible if 0 <= points[i][0] < width and 0 <= points[i][1] < height}
    flags = []
    if not {11,12,23,24}.issubset(inside):
        flags.append('uncertain_torso')
    def distance(a,b):
        return math.hypot(a[0]-b[0], a[1]-b[1])
    shoulder = [(points[11][i]+points[12][i])/2 for i in range(2)]
    hip = [(points[23][i]+points[24][i])/2 for i in range(2)]
    torso = distance(shoulder,hip)
    if torso < 1:
        raise ValueError('Degenerate torso scale.')
    raised = {side: (bool(points[wrist][1] < points[arm][1]) if {arm,wrist}.issubset(inside) else None)
              for side,arm,wrist in [('left',11,15),('right',12,16)]}
    lengths = {f'{a}-{b}':distance(points[a],points[b])/torso for a,b in BONES if {a,b}.issubset(inside)}
    body = {str(i):[float(points[i][0]),float(points[i][1])] for i in inside}
    jump = None
    length_change = None
    if previous and not flags and not previous['flags']:
        common = set(body)&set(previous['joints'])
        scale = max(torso,previous['torso_px'])
        jump = max((distance(body[i],previous['joints'][i])/scale for i in common),default=None)
        changes = [max(v,previous['bone_lengths'][k])/min(v,previous['bone_lengths'][k])
                   for k,v in lengths.items() if k in previous['bone_lengths'] and min(v,previous['bone_lengths'][k])>.03]
        length_change = max(changes,default=None)
        if jump is not None and jump > .75:
            flags.append('landmark_jump')
        if length_change is not None and length_change > 2:
            flags.append('projected_limb_length_jump')
    return {'joints':body,'visible_joints':sorted(visible),'in_frame_joints':sorted(inside),
            'torso_px':torso,'bone_lengths':lengths,'raised':raised,
            'max_joint_step_torsos':jump,'max_bone_length_ratio':length_change,'flags':flags}


def load_evaluator():
    import cv2
    manifest = json.loads((ROOT/'config/body-evaluator.json').read_text())
    for name,spec in manifest['files'].items():
        path=CACHE/name
        if path.resolve().parent != CACHE.resolve() or path.stat().st_size != spec['bytes']:
            raise ValueError('Missing or unexpected evaluator asset.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Evaluator hash mismatch: '+name)
    modules={}
    for name in ['mp_persondet','mp_pose']:
        spec=importlib.util.spec_from_file_location('ai_mate_review_'+name,CACHE/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules[name]=module
    cv2.setNumThreads(2)
    detector=modules['mp_persondet'].MPPersonDet(str(CACHE/'person_detection_mediapipe_2023mar.onnx'),
                                               backendId=cv2.dnn.DNN_BACKEND_OPENCV,targetId=cv2.dnn.DNN_TARGET_CPU)
    pose=modules['mp_pose'].MPPose(str(CACHE/'pose_estimation_mediapipe_2023mar.onnx'),
                                 backendId=cv2.dnn.DNN_BACKEND_OPENCV,targetId=cv2.dnn.DNN_TARGET_CPU)
    return cv2,detector,pose,manifest


def inspect_frame(image, detector, pose, previous=None):
    people=detector.infer(image)
    if len(people) != 1:
        return {'person_count':len(people),'flags':['person_count']}
    result=pose.infer(image,people[0].copy())
    if result is None:
        return {'person_count':1,'flags':['missing_pose']}
    points=result[1][:33].tolist()
    try:
        metrics=landmark_metrics(points,image.shape[1],image.shape[0],previous)
    except ValueError:
        return {'person_count':1,'flags':['invalid_pose']}
    return {'person_count':1,'pose_confidence':float(result[-1]),'landmarks':points,**metrics}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'voice-video-(qualification|soak)-[a-z0-9-]{1,32}',args.source) or not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):
        parser.error('Use a retained synthetic call source and fresh lowercase label.')
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(('127.0.0.1',8766)) == 0:
            parser.error('Finish call timing before running CPU frame analysis.')
    source=ROOT/'generated/local-app/audit'/args.source
    if (source.resolve().parent != (ROOT/'generated/local-app/audit').resolve()
            or (source/'retained-media').resolve().parent != source.resolve()):
        parser.error('The synthetic source must stay inside the local audit directory.')
    if not (source/'browser-done.json').is_file():
        parser.error('The call driver has not finished.')
    raw=json.loads((source/'qualification.json').read_text())
    reviewed=json.loads((source/'frame-review.json').read_text())['reviews']
    if not raw.get('results') or not reviewed:
        parser.error('No completed retained clips are available for body review.')
    reviews={(r['id'],r['chunk']):r for r in reviewed}
    output=ROOT/'generated/local-app/audit'/('body-'+args.label)
    if output.exists():
        parser.error('Preserve prior evidence; choose a fresh label.')
    cv,detector,pose,manifest=load_evaluator()
    output.mkdir()
    report={'source':args.source,'source_revision':manifest['source_commit'],'opencv':cv.__version__,
            'evaluator_sha256':hashlib.sha256((ROOT/'config/body-evaluator.json').read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':__doc__,'clips':[],'complete':False}
    started=time.perf_counter()
    try:
        controls=None
        for row in raw['results']:
            job=row.get('job')
            if not job:continue
            if not re.fullmatch(r'[a-f0-9]{32}',job['id']):raise ValueError('Invalid retained job ID.')
            for chunk in job['chunks']:
                index=chunk['index']
                if type(index) is not int or not 0 <= index < 100:raise ValueError('Invalid retained chunk.')
                name=f'{job["id"]}-{index}.mp4';path=source/'retained-media'/name
                if path.resolve().parent != (source/'retained-media').resolve() or not 0 < path.stat().st_size <= 64_000_000:
                    raise ValueError('Unexpected retained video.')
                review=reviews[(job['id'],index)]
                if hashlib.sha256(path.read_bytes()).hexdigest() != review['video_sha256']:
                    raise ValueError('Video changed after its frame review.')
                capture=cv.VideoCapture(str(path));rows=[];previous=None
                try:
                    while len(rows)<1801:
                        ok,frame=capture.read()
                        if not ok:break
                        if controls is None:
                            black=inspect_frame(frame*0,detector,pose)
                            controls={'black_frame_flags':black['flags'],'black_frame_detected':bool(black['flags'])}
                        result=inspect_frame(frame,detector,pose,previous)
                        if ('mirror_control' not in controls and result.get('raised') == {'left':False,'right':True}):
                            mirrored=inspect_frame(cv.flip(frame,1),detector,pose)
                            controls['mirror_control']={'observed':mirrored.get('raised'),
                                'left_right_swap_detected':mirrored.get('raised') == {'left':True,'right':False},
                                'case':row['case'],'frame':len(rows),
                                'scope':'Geometric flip sensitivity; not anatomical ground truth.'}
                        result['frame']=len(rows)
                        result['time_s']=review['frames'][len(rows)]['time_s']
                        rows.append(result);previous=result if 'joints' in result else None
                finally:capture.release()
                if not rows or len(rows)>1800 or len(rows)!=review['summary']['decoded_frames']:
                    raise ValueError('Body review frame coverage differs from decoded-frame audit.')
                summary={'case':row['case'],'cycle':row['cycle'],'id':job['id'],'chunk':index,
                         'frames':len(rows),'flagged_frames':[r['frame'] for r in rows if r['flags']],
                         'right_raised_frames':sum(r.get('raised',{}).get('right') is True for r in rows),
                         'left_raised_frames':sum(r.get('raised',{}).get('left') is True for r in rows),
                         'video_sha256':review['video_sha256'],'frames_file':name+'.json'}
                (output/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
                report['clips'].append(summary)
                print(json.dumps(summary),flush=True)
        if not report['clips']:
            raise ValueError('No retained clips were evaluated.')
        report['controls']=controls
        report['complete']=True
    finally:
        report['elapsed_s']=time.perf_counter()-started
        (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
