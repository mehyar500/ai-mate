"""Isolated real-media benchmark server. No cloud requests or private memory.

Port 8766; exits after 150 seconds. Readiness and result paths contain only
synthetic data. The normal demo on 8765 is never mutated by this script.
"""
import argparse
from functools import partial
import json
from pathlib import Path
import shutil
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.engine import CompanionEngine, configure_runtime
from local_app.models import Models
from local_app.server import Handler, ThreadingHTTPServer
from scripts.benchmark_cloud_speech import CASES


class SyntheticModels(Models):
    action = 'none'
    interruption = False
    def plan(self, snapshot, text, mode, scene, available, event):
        if self.interruption:
            action = 'closer' if text == 'approach' else 'farther' if text == 'return' else 'none'
            reply = CASES['long'] if action == 'closer' else 'I am right here. The garden is peaceful.'
            return {'reply': reply, 'presentation': mode, 'scene': 'fullbody', 'action': action, 'facts': []}
        return {'reply': CASES['long'], 'presentation': mode, 'scene': 'fullbody',
                'action': self.action, 'facts': []}

    def transcribe(self, raw):
        if self.interruption:
            return {b'\x01': 'approach', b'\x02': 'hello', b'\x03': 'return'}[raw]
        return 'Please count from one to twenty-five.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--whole', action='store_true')
    parser.add_argument('--batch-size', type=int, choices=[8, 16], default=8)
    parser.add_argument('--action', choices=['none', 'closer'], default='none')
    parser.add_argument('--interruption', action='store_true')
    parser.add_argument('--trial', choices=['early', 'middle'], default='early')
    args = parser.parse_args()
    label = 'whole' if args.whole else 'phrases'
    if args.batch_size != 8:
        label += '-b' + str(args.batch_size)
    if args.action == 'closer':
        label += '-approach'
    if args.interruption:
        label = 'interruption' + ('-middle' if args.trial == 'middle' else '')
    folder = ROOT / 'generated/local-app/audit' / ('speech-' + label)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ['fullbody.png', 'performance-near.png', 'performance-closer.mp4',
                 'performance-farther.mp4', 'performance.json', 'idle-fullbody.mp4',
                 'idle-fullbody.json', 'idle-near.mp4', 'idle-near.json']:
        shutil.copyfile(ROOT/'generated/local-app'/name, folder/name)
    configure_runtime()
    app = CompanionEngine(folder)
    app.store.reset()  # This dedicated synthetic database only.
    app.scene = 'fullbody'
    app.models = SyntheticModels()
    app.models.action = args.action
    app.models.interruption = args.interruption
    renderer = app.models.load_visual()
    renderer.render = partial(renderer.render, batch_size=args.batch_size)
    audio = folder/'warm.wav'
    app.models.speech('Hello there.', audio)
    renderer.prepare('fullbody')
    renderer.render(audio, folder/'warm.mp4', threading.Event(), 'fullbody', streaming=True,
                    motion_path=app.idle_video, loop_motion=True, reuse_motion=True)
    app.ready = True
    server = ThreadingHTTPServer(('127.0.0.1', 8766), Handler)
    server.daemon_threads = True
    server.app = app
    from local_app.speech import speech_phrases
    splitter = (lambda text: [text]) if args.whole else speech_phrases
    with patch('local_app.speech.speech_phrases', side_effect=splitter):
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        print(json.dumps({'ready': True, 'label': label, 'url': 'http://127.0.0.1:8766'}), flush=True)
        # A local file marks browser completion; no public shutdown endpoint.
        done = folder/'browser-done.json'
        done.unlink(missing_ok=True)
        deadline = time.monotonic() + 150
        try:
            saved_stop = False
            while time.monotonic() < deadline and not done.exists():
                if args.interruption and not saved_stop:
                    with app.lock:
                        if app.pose and app.pose[1].name.startswith('playback-'):
                            shutil.copyfile(app.pose[1], folder/'interrupted-pose.png')
                            saved_stop = True
                time.sleep(.2)
            app.cancel()
            while app.busy:
                time.sleep(.05)
            jobs = [app.job(key) for key in app.jobs]
            (folder/'engine-results.json').write_text(json.dumps(jobs, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'finished': True, 'label': label, 'jobs': len(jobs)}), flush=True)
        finally:
            server.shutdown(); server.server_close()


if __name__ == '__main__': main()
