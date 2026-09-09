"""Synthetic call suites through real ASR, hosted planning, speech and video.

Uses only a new disposable directory and localhost:8766. Existing Cloudflare
credentials are used for one warm-up and up to 120 bounded scripted turns;
no private conversation is read. Drivers supply only the fixed fixtures.
"""
import argparse
import json
import os
import re
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
    parser.add_argument('--trial', choices=['baseline', 'revised', 'selected', 'wave', 'qualification', 'soak'], required=True)
    parser.add_argument('--label', default='')
    parser.add_argument('--performance-label', default='', help='Use a reviewed isolated candidate asset bundle.')
    parser.add_argument('--decoder', choices=['torch','tensorrt','tensorrt-reviewed'], default='torch', help='Torch, experimental engine, or the reviewed runtime path.')
    parser.add_argument('--fragment-ms',type=int,choices=[100,200],help='Isolated FFmpeg fragment-duration override.')
    parser.add_argument('--asr-device',choices=['cpu','cuda'],help='Isolated speech-recognition device override.')
    parser.add_argument('--tts-device',choices=['cpu','cuda'],help='Isolated speech-synthesis device override.')
    args = parser.parse_args()
    if args.label and not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label, digits and hyphens only.')
    if args.performance_label and not re.fullmatch(r'[a-z0-9-]{1,32}', args.performance_label):
        parser.error('Use a short lowercase performance label.')
    assets = ROOT/'generated/local-app'
    if args.performance_label:
        assets=assets/'audit'/('performance-'+args.performance_label)
        from local_app.performance import load_reviewed_performance
        from local_app.idle import load_reviewed_idle
        performance=load_reviewed_performance(assets)
        if not performance or not all(load_reviewed_idle(assets,pose) for pose in ['base','near']):
            parser.error('The candidate needs reviewed, matching performance and listening manifests.')
        if args.trial in {'wave','qualification','soak'} and ('base','wave') not in performance:
            parser.error('This trial also needs a reviewed, matching wave.')
    folder = ROOT/'generated/local-app/audit'/('voice-video-'+args.trial+('-'+args.label if args.label else ''))
    folder.mkdir(parents=True, exist_ok=False)
    for name in ['fullbody.png', 'performance-near.png', 'performance-closer.mp4',
                 'performance-farther.mp4', 'performance.json', 'idle-fullbody.mp4',
                 'idle-fullbody.json', 'idle-near.mp4', 'idle-near.json']:
        shutil.copyfile(assets/name, folder/name)
    if args.trial in {'wave','qualification','soak'}:
        for name in ['performance-wave.mp4','performance-wave.json']:
            shutil.copyfile((assets if args.performance_label else ROOT/'generated/local-app/audit')/name, folder/name)
    configure_runtime()
    if args.asr_device is not None:os.environ['AI_MATE_ASR_DEVICE']=args.asr_device
    if args.tts_device is not None:os.environ['AI_MATE_TTS_DEVICE']=args.tts_device
    os.environ['AI_MATE_VISUAL_DECODER']='tensorrt' if args.decoder=='tensorrt-reviewed' else 'torch'
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
    cases = [('wave','Please wave hello with your right hand.'), *CASES,
             ('return','Please step back to the full body view.')] if args.trial == 'wave' else CASES
    specifications = json.loads((ROOT/'config/video-call-qualification.json').read_text()) if args.trial in {'qualification','soak'} else [dict(case=case,prompt=prompt) for case,prompt in cases]
    for spec in specifications:
        case, prompt = spec['case'], spec['prompt']
        target = folder/(case+'.wav')
        duration = app.models.speech(prompt, target)
        fixtures.append(dict(spec, duration_s=duration))
    renderer = app.models.load_visual()
    if args.fragment_ms is not None:
        original_render=renderer.render
        def render_fragment_trial(*render_args,**render_kwargs):
            return original_render(*render_args,**{**render_kwargs,'fragment_ms':args.fragment_ms})
        renderer.render=render_fragment_trial
    if args.decoder=='tensorrt':
        sys.path.insert(0,str(ROOT/'.cache/tensorrt-deps'))
        from scripts.trt_vae_runtime import ExperimentalDecoder
        renderer.decode_prediction=ExperimentalDecoder(renderer.torch,ROOT/'generated/local-app/audit/visual-trt-fp16')
        renderer.decoder_backend='tensorrt-experiment'
    renderer.prepare('fullbody')
    renderer.render(folder/'greeting.wav', folder/'warm.mp4', event, 'fullbody',
                    streaming=True, motion_path=app.idle_video, loop_motion=True,
                    reuse_motion=True)
    app.prime_reviewed_visual(renderer, event)
    app.ready = True
    (folder/'benchmark-settings.json').write_text(json.dumps({
        'speech_model':'Kokoro-82M ONNX v1.0','speech_voice':'af_sarah',
        'speech_cpu_threads':app.models.speech_threads,'decoder':args.decoder,
        'speech_runtime':app.models.speech_runtime,
        'fragment_ms_override':args.fragment_ms,
        'asr_device':app.models.asr_device,'asr_compute_type':app.models.asr_compute_type,'asr_warm_s':app.models.asr_warm_s,
        'performance_label':args.performance_label,'visual_warmup':app.visual_warmup,
        'scope':'Synthetic isolated call; no private conversation or active preview selection.'
    },indent=2)+'\n',encoding='utf-8')
    (folder/'fixtures.json').write_text(json.dumps(fixtures, indent=2)+'\n')
    server = ThreadingHTTPServer(('127.0.0.1', 8766), Handler)
    server.daemon_threads = True
    server.app = app
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    print(json.dumps({'ready': True, 'trial': args.trial, 'visual_warmup': app.visual_warmup}), flush=True)
    measurement_started=time.monotonic()
    deadline = measurement_started+(2160 if args.trial == 'soak' else 600)
    memory_samples=[]
    next_memory_sample=0
    try:
        while time.monotonic()<deadline and not (folder/'browser-done.json').exists():
            if time.monotonic()>=next_memory_sample:
                free,total=renderer.torch.cuda.mem_get_info()
                memory_samples.append({'elapsed_s':round(time.monotonic()-measurement_started,3),
                                       'used_mib':round((total-free)/1048576,3),'free_mib':round(free/1048576,3)})
                next_memory_sample=time.monotonic()+5
            time.sleep(.2)
        app.cancel()
        while app.busy:
            time.sleep(.05)
        jobs = [app.job(key) for key in app.jobs]
        (folder/'engine-results.json').write_text(json.dumps(jobs, indent=2)+'\n')
        (folder/'gpu-memory.json').write_text(json.dumps({'scope':'Whole-GPU used/free memory sampled every five seconds, including other processes; not an exact peak or per-worker allocation.',
            'samples':memory_samples,'max_sampled_used_mib':max((r['used_mib'] for r in memory_samples),default=None),
            'min_sampled_free_mib':min((r['free_mib'] for r in memory_samples),default=None)},indent=2)+'\n')
        print(json.dumps({'finished': True, 'jobs': len(jobs)}), flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
