"""Run a neutral image-to-video motion test through the loopback ComfyUI API."""
import argparse
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8188'
CHECKPOINT = 'ltxv-2b-0.9.8-distilled-fp8.safetensors'
ENCODER = 't5xxl_fp8_e4m3fn.safetensors'
PROMPT = ('A realistic full-body video of an adult woman standing on a stone garden path. '
          'She wears a cream sweater, blue jeans and white shoes. She raises her right hand '
          'from her side until her open palm is beside her head and waves hello at the camera. '
          'Her right elbow bends and her fingers spread as her hand moves from side to side. '
          'Her left hand stays relaxed beside her hip. She smiles naturally, then lowers her '
          'right hand back to her side. Her feet stay planted on the path. The camera remains '
          'still and her whole body stays visible. Soft daylight illuminates her face and '
          'the green plants behind her. Natural human movement, continuous realistic footage.')


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BASE+path, data=body, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def workflow(width, height, frames, seed):
    def node(kind, **inputs):
        return {'class_type':kind, 'inputs':inputs}
    return {
        '1':node('CheckpointLoaderSimple', ckpt_name=CHECKPOINT),
        '2':node('CLIPLoader', clip_name=ENCODER, type='ltxv', device='default'),
        '3':node('CLIPTextEncode', clip=['2',0], text=PROMPT),
        '4':node('CLIPTextEncode', clip=['2',0], text=''),
        '5':node('LoadImage', image='fullbody.png'),
        '6':node('LTXVConditioning', positive=['3',0], negative=['4',0], frame_rate=24),
        '7':node('LTXVImgToVideo', positive=['6',0], negative=['6',1], vae=['1',2],
                 image=['5',0], width=width, height=height, length=frames, batch_size=1, strength=1),
        # Exact allowed_inference_steps read from this pinned checkpoint's metadata.
        '8':node('ManualSigmas', sigmas='1.0, 0.9937, 0.9875, 0.9812, 0.975, 0.9094, 0.725, 0.4219, 0'),
        '9':node('KSamplerSelect', sampler_name='euler'),
        '10':node('SamplerCustom', model=['1',0], add_noise=True, noise_seed=seed, cfg=1,
                  positive=['7',0], negative=['7',1], sampler=['9',0], sigmas=['8',0], latent_image=['7',2]),
        '11':node('VAEDecode', samples=['10',1], vae=['1',2]),
        '12':node('SaveWEBM', images=['11',0], filename_prefix='motion/ltx-wave', codec='vp9', fps=24, crf=18),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=384)
    parser.add_argument('--height', type=int, default=576)
    parser.add_argument('--frames', type=int, default=49)
    parser.add_argument('--seed', type=int, default=42)
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
    graph = workflow(opts.width, opts.height, opts.frames, opts.seed)
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
            record = {'wall_s':round(time.perf_counter()-started,3), 'seed':opts.seed,
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
