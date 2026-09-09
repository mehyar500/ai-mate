"""Compare neutral retained speech on both poses with bounded MuseTalk face crops.

No dialogue API, TTS, private memory, live configuration change or timing fix.
Outputs use the existing every-frame and SyncNet review formats.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from local_app.media import load_reviewed_idle
from local_app.visual import PortraitRenderer
from scripts.review_lip_sync import preview_idle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label.')
    source = ROOT / 'generated/local-app/audit/voice-video-soak-gpu-pcm'
    folder = ROOT / 'generated/local-app/audit' / ('voice-video-qualification-' + args.label)
    if folder.exists():
        parser.error('Preserve previous evidence; use a fresh label.')
    cases = [r for r in json.loads((source / 'qualification.json').read_text())['results']
             if r['cycle'] == 1 and r['case'] in {'description', 'unsupported'}]
    if len(cases) != 2:
        raise ValueError('Two retained synthetic phrases are required.')
    sources = {pose: load_reviewed_idle(source, pose) for pose in ['base', 'near']}
    if not all(sources.values()):
        raise ValueError('Both source clips must have reviewed matching manifests.')
    preview_idle()
    renderer = PortraitRenderer(decoder_backend='tensorrt')
    folder.mkdir()
    media = folder / 'retained-media'
    media.mkdir()
    results = {'scope': 'Offline neutral crop comparison. All poses use the same two retained synthetic WAVs. Source images reviewed before rendering. Not a call-latency or human-quality qualification.',
               'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'source_videos_sha256': {pose: hashlib.sha256(path.read_bytes()).hexdigest() for pose, path in sources.items()},
               'results': []}
    started = time.perf_counter()
    try:
        for shift in [-.10, -.05, 0]:
            renderer.face_shift = shift
            for pose, path in sources.items():
                preview_idle()
                renderer.prime_motion([path], threading.Event())
                for case in cases:
                    preview_idle()
                    identifier = uuid.uuid4().hex
                    wav, video = (media / (identifier + '-0' + suffix) for suffix in ['.wav', '.mp4'])
                    source_wav = source / 'retained-media' / (case['job']['id'] + '-0.wav')
                    shutil.copyfile(source_wav, wav)
                    result = renderer.render(wav, video, threading.Event(), 'fullbody', streaming=True,
                                             motion_path=path, loop_motion=True, reuse_motion=True)
                    chunk = {'index': 0, 'text': case['job']['text'], 'audio': '/media/' + wav.name,
                             'video': '/media/' + video.name, 'duration_s': case['job']['chunks'][0]['duration_s'],
                             'render': result, 'complete': True}
                    row = {'case': case['case'], 'cycle': 1, 'input': 'offline-retained-audio', 'failures': [],
                           'face_shift': shift,
                           'job': {'id': identifier, 'action': 'none', 'state': 'complete', 'prepared_pose': pose,
                                   'text': case['job']['text'], 'chunks': [chunk]}}
                    results['results'].append(row)
                    print(json.dumps({'pose': pose, 'face_shift': shift, 'case': case['case'], 'render_s': result['render_s']}), flush=True)
        results['complete'] = True
    finally:
        results['elapsed_s'] = time.perf_counter() - started
        (folder / 'qualification.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
