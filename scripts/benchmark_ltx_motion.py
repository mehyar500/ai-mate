"""Run a neutral image-to-video motion test through the loopback ComfyUI API."""
import argparse
import json
import shutil
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from local_app.motion import CHECKPOINT, ENCODER, PROMPTS, workflow
BASE = 'http://127.0.0.1:8188'
def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BASE+path, data=body, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=384)
    parser.add_argument('--height', type=int, default=576)
    parser.add_argument('--frames', type=int, default=49)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--action', choices=tuple(PROMPTS), default='wave')
    parser.add_argument('--reference', choices=['fullbody','fullbody-candidate','mira'], default='fullbody')
    parser.add_argument('--encoder', choices=['h264','vp9'], default='h264')
    parser.add_argument('--wait-models', type=int, default=0)
    opts = parser.parse_args()
    if any(v < 128 or v % 32 for v in (opts.width, opts.height)) or opts.frames < 9 or opts.frames % 8 != 1:
        parser.error('Dimensions must be multiples of 32; frames must be 8n+1.')
    model_root = ROOT / '.cache/local-poc/ComfyUI/models'
    required = [model_root/'checkpoints'/CHECKPOINT, model_root/'text_encoders'/ENCODER]
    deadline = time.monotonic()+opts.wait_models
    while not all(path.is_file() for path in required):
        if time.monotonic() >= deadline:
            raise RuntimeError('LTX checkpoint/text encoder download is incomplete.')
        print('Waiting for existing LTX model downloads.', flush=True)
        time.sleep(min(30, max(0,deadline-time.monotonic())))
    graph = workflow(opts.width, opts.height, opts.frames, opts.seed, opts.action, opts.encoder)
    source = ROOT/'generated/local-app'/(opts.reference+'.png')
    target = ROOT/'.cache/local-poc/ComfyUI/input'/('benchmark-'+opts.reference+'.png')
    shutil.copyfile(source,target)
    graph['5']['inputs']['image'] = target.name
    audit = ROOT/'generated/local-app/audit'
    audit.mkdir(parents=True, exist_ok=True)
    (audit/'ltx-motion-api.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
    started = time.perf_counter()
    submitted = request('/prompt', {'prompt':graph})
    key = submitted['prompt_id']
    print(f'Queued LTX motion benchmark: {key}',flush=True)
    for _ in range(900):
        history = request('/history/'+key)
        if key in history:
            result = history[key]
            messages = result.get('status', {}).get('messages', [])
            times = {event:data['timestamp'] for event,data in messages if 'timestamp' in data}
            execution_s = ((times['execution_success']-times['execution_start'])/1000
                           if 'execution_success' in times and 'execution_start' in times else None)
            record = {'wall_s':round(time.perf_counter()-started,3), 'seed':opts.seed,
                      'server_execution_s':execution_s, 'action':opts.action, 'encoder':opts.encoder, 'reference':opts.reference,
                      'resolution':[opts.width,opts.height], 'frames':opts.frames,
                      'checkpoint':CHECKPOINT, 'status':result.get('status'), 'outputs':result.get('outputs')}
            (audit/f'ltx-motion-{key}.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
            print(json.dumps(record),flush=True)
            if result.get('status',{}).get('status_str') != 'success':
                raise RuntimeError('ComfyUI motion generation failed; see the benchmark record.')
            return
        time.sleep(1)
    raise RuntimeError('ComfyUI benchmark timed out; inspect its local queue before retrying.')


if __name__ == '__main__':
    main()
