"""Three synthetic WAV turns through real ASR, hosted planning, speech and video.

Uses only a new disposable directory and localhost:8766. Existing Cloudflare
credentials are used for four bounded plans including warm-up; no private
conversation is read. The browser driver supplies only these fixed fixtures.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app.engine import CompanionEngine, configure_runtime
from local_app.models import Models
from local_app.server import Handler, ThreadingHTTPServer

CASES = [
    ('greeting', 'Hi Mira, how are you today?'),
    ('memory', "What is my dog's name?"),
    ('approach', 'Could you come closer and say hello?'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', choices=['baseline', 'revised', 'selected'], required=True)
    args = parser.parse_args()
    folder = ROOT/'generated/local-app/audit'/('voice-video-'+args.trial)
    folder.mkdir(parents=True, exist_ok=False)
    for name in ['fullbody.png', 'performance-near.png', 'performance-closer.mp4',
                 'performance-farther.mp4', 'performance.json', 'idle-fullbody.mp4',
                 'idle-fullbody.json', 'idle-near.mp4', 'idle-near.json']:
        shutil.copyfile(ROOT/'generated/local-app'/name, folder/name)
    configure_runtime()
    app = CompanionEngine(folder)
    app.scene = 'fullbody'
    app.store.remember('My dog is named Maple.')
    app.models = Models()
    if app.models.conversation.provider != 'cloudflare':
        raise ValueError('This benchmark requires the already configured Cloudflare provider.')
    event = threading.Event()
    app.models.plan({'memory': '', 'turns': []}, 'Say hello briefly.', 'video',
                    'fullbody', ['fullbody'], event)
    fixtures = []
    for case, prompt in CASES:
        target = folder/(case+'.wav')
        duration = app.models.speech(prompt, target)
        fixtures.append({'case': case, 'prompt': prompt, 'duration_s': duration})
    renderer = app.models.load_visual()
    renderer.prepare('fullbody')
    renderer.render(folder/'greeting.wav', folder/'warm.mp4', event, 'fullbody',
                    streaming=True, motion_path=app.idle_video, loop_motion=True,
                    reuse_motion=True)
    app.prime_reviewed_visual(renderer, event)
    app.ready = True
    (folder/'fixtures.json').write_text(json.dumps(fixtures, indent=2)+'\n')
    server = ThreadingHTTPServer(('127.0.0.1', 8766), Handler)
    server.daemon_threads = True
    server.app = app
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'ready': True, 'trial': args.trial, 'visual_warmup': app.visual_warmup}), flush=True)
    deadline = time.monotonic()+240
    try:
        while time.monotonic()<deadline and not (folder/'browser-done.json').exists():
            time.sleep(.2)
        app.cancel()
        while app.busy:
            time.sleep(.05)
        jobs = [app.job(key) for key in app.jobs]
        (folder/'engine-results.json').write_text(json.dumps(jobs, indent=2)+'\n')
        print(json.dumps({'finished': True, 'jobs': len(jobs)}), flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
