"""Compare audio alignment/face crops on reviewed, fully clothed synthetic media."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.visual import PortraitRenderer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion', action='store_true')
    args = parser.parse_args()
    folder = ROOT/'generated/local-app/audit'/('visual-quality-motion' if args.motion else 'visual-quality')
    folder.mkdir(parents=True, exist_ok=True)
    # Existing known synthetic sentence, no private user speech or API call.
    audio = ROOT/'generated/local-app/audit/cloud-compare-kokoro-normal.wav'
    if not audio.is_file():
        raise FileNotFoundError('Run the documented synthetic speech comparison first.')
    renderer = PortraitRenderer()
    rows = []
    sources = [('approach','performance-closer.mp4'), ('return','performance-farther.mp4')] if args.motion else [('near','idle-near.mp4'),('body','idle-fullbody.mp4')]
    variants = [('legacy', -.04, 4), ('higher', -.10, 6)] if args.motion else [('legacy', -.04, 4), ('aligned', -.04, 6), ('higher', -.10, 6), ('highest', -.16, 6)]
    for scene, source in sources:
        motion = ROOT/'generated/local-app'/source
        for label, shift, left in variants:
            renderer.face_shift = shift
            output = folder/(scene+'-'+label+'.mp4')
            with patch('local_app.visual.audio_left_padding', return_value=left):
                metrics = renderer.render(audio, output, threading.Event(), 'fullbody', streaming=True,
                    motion_path=motion, loop_motion=not args.motion, reuse_motion=True)
            rows.append({'scene':scene, 'candidate':label, 'face_shift':shift, 'left_padding':left,
                         'metrics':metrics, 'video_sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
            print(json.dumps({'scene':scene,'candidate':label,'render_s':metrics['render_s']}),flush=True)
    report = {'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(), 'rows':rows,
              'limits':'Same synthetic speech and reviewed footage. No microphone, private conversation or remote inference. Visual/phoneme review required; speed is not controlled for source-cache warmness.'}
    (folder/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
