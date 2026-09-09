"""Bounded local LTX motion generation through a loopback-only ComfyUI worker."""
import json
import math
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import urllib.request

from .models import CACHE, ROOT, check_cancel

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
PROMPTS = {
    'idle': ('A continuous photographic video of the adult woman in the reference image listening '
             'quietly to the person behind the camera. She briefly turns her head to glance to her left, '
             'then turns back toward the camera and gives a gentle nod. She blinks naturally. Her lips '
             'remain softly closed, her arms rest beside her hips, and her feet remain planted. '
             'Her identity, clothing, body position, framing and surroundings remain unchanged. '
             'The camera stays perfectly fixed. Calm subtle natural human movement.'),
    'wave': PROMPT,
    'closer': ('A continuous realistic video of an adult woman wearing a cream sweater, blue jeans '
               'and white shoes on a stone garden path. She looks at the camera, smiles and walks '
               'forward toward it, taking two natural steps. Her legs and feet visibly move and '
               'her arms swing gently beside her body. She becomes larger in the frame as she '
               'approaches, then stops. The camera stays completely stationary: the garden and '
               'plant pots remain fixed in the background. Natural human anatomy and body movement, '
               'consistent face, soft daylight, realistic continuous footage.'),
    'farther': ('A continuous realistic video of an adult woman wearing a cream sweater, blue jeans '
                'and white shoes on a stone garden path. Facing the camera, she carefully takes '
                'two steps backward down the path. Her knees bend and her feet visibly lift and '
                'move. She becomes smaller in the frame and more of the path becomes visible '
                'around her. She smiles and settles into a relaxed standing position. The camera '
                'does not move or zoom; the plants and garden remain stationary. Consistent face, '
                'natural body movement and anatomy, soft daylight, realistic continuous footage.'),
}


def workflow(width, height, frames, seed, action='wave', encoder='h264', end_image=None):
    def node(kind, **inputs):
        return {'class_type':kind, 'inputs':inputs}
    graph = {
        '1':node('CheckpointLoaderSimple', ckpt_name=CHECKPOINT),
        '2':node('CLIPLoader', clip_name=ENCODER, type='ltxv', device='default'),
        '3':node('CLIPTextEncode', clip=['2',0], text=PROMPTS[action]),
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
        '12':node('SaveWEBM', images=['11',0], filename_prefix='motion/ltx-'+action, codec='vp9', fps=24, crf=18),
    }
    if encoder == 'h264':
        graph['12'] = node('CreateVideo', images=['11',0], fps=24)
        graph['13'] = node('SaveVideo', video=['12',0], filename_prefix='motion/ltx-'+action,
                           format='mp4', **{'format.codec':'h264'})
    if end_image:
        graph['14'] = node('LoadImage', image=end_image)
        graph['15'] = node('LTXVAddGuide', positive=['7',0], negative=['7',1],
                           latent=['7',2], vae=['1',2], image=['14',0], frame_idx=-1, strength=1.0)
        graph['10']['inputs'].update(positive=['15',0], negative=['15',1], latent_image=['15',2])
        graph['16'] = node('LTXVCropGuides', positive=['15',0], negative=['15',1], latent=['10',1])
        graph['11']['inputs']['samples'] = ['16',2]
    return graph


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BASE+path, data=body, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def reverse_approach(source, destination, cancel):
    """Reuse the immediately preceding generated approach in reverse; no diffusion.

    Only the engine selects these private files. New speech/lips are added later.
    """
    check_cancel(cancel)
    source, destination = Path(source), Path(destination)
    folder = (ROOT/'generated/local-app').resolve()
    if (source.resolve().parent != folder or destination.resolve().parent != folder
            or not re.fullmatch(r'[a-f0-9]{32}-\d+-return\.mp4', source.name)
            or not re.fullmatch(r'[a-f0-9]{32}-\d+-motion\.mp4', destination.name)):
        raise ValueError('Return motion must use private app-owned media.')
    if not source.is_file() or source.stat().st_size > 40_000_000:
        raise ValueError('The preceding movement is missing or too large.')
    started = time.perf_counter()
    info = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                           'stream=width,height,nb_frames,duration','-of','json',str(source)],
                          capture_output=True, timeout=5, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if info.returncode:
        raise RuntimeError('The preceding movement could not be read.')
    streams = json.loads(info.stdout).get('streams', [])
    if len(streams) != 1 or not 0 < float(streams[0].get('duration', 0)) <= 5:
        raise ValueError('Return motion requires a short completed movement.')
    stream = streams[0]
    if not 0 < stream.get('width',0) <= 768 or not 0 < stream.get('height',0) <= 1152:
        raise ValueError('The preceding movement exceeds the local size limit.')
    check_cancel(cancel)
    command = ['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-an',
               '-vf','reverse','-c:v','libx264','-preset','ultrafast','-crf','18','-threads','2',
               '-pix_fmt','yuv420p',str(destination)]
    process = subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        while process.poll() is None:
            check_cancel(cancel)
            if time.perf_counter()-started > 15:
                raise RuntimeError('Return motion encoding timed out.')
            cancel.wait(.02)
        if process.returncode:
            raise RuntimeError('Return motion encoding failed.')
        check_cancel(cancel)
        return {'motion_s':round(time.perf_counter()-started,3),'action':'farther',
                'motion_source':'reversed_previous_approach','fresh_body_generation':False,
                'motion_frames':int(stream.get('nb_frames',0)),
                'motion_resolution':f"{stream['width']}x{stream['height']}"}
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait()
        destination.unlink(missing_ok=True)
        raise
    finally:
        process.stderr.close()


def generate(scene, action, duration, cancel, destination, reference_path=None, media_directory=None):
    """Generate one fresh action. No model-authored URLs, paths or graph nodes."""
    if scene not in {'mira','garden','cafe','fullbody'} or action not in PROMPTS:
        raise ValueError('Unsupported motion scene or action.')
    check_cancel(cancel)
    root = CACHE/'ComfyUI'
    tag = 'mate-'+secrets.token_hex(16)
    source = root/'input'/(tag+'.png')
    source.parent.mkdir(parents=True, exist_ok=True)
    media_directory = Path(media_directory) if media_directory is not None else ROOT/'generated/local-app'
    reference = Path(reference_path) if reference_path else media_directory/(scene+'.png')
    if reference.resolve().parent != media_directory.resolve() or reference.suffix != '.png':
        raise ValueError('The motion reference must be an app-owned image.')
    shutil.copyfile(reference, source)
    frames = min(97, max(49, math.ceil(duration*24/8)*8+1))
    if action in {'wave','idle'}:
        # Two-second start/end-guided tests stayed still; allow time to raise
        # and lower the arm. Three-second trials moved across three fresh seeds.
        frames = max(73,frames)
    graph = workflow(384,576,frames,secrets.randbits(32),action,
                     end_image=source.name if action in {'wave','idle'} else None)
    graph['5']['inputs']['image'] = source.name
    graph['13']['inputs']['filename_prefix'] = 'motion/'+tag
    started = time.perf_counter()
    prompt_id = None
    try:
        prompt_id = request('/prompt', {'prompt':graph})['prompt_id']
        deadline = time.monotonic()+90
        while time.monotonic() < deadline:
            if cancel.is_set():
                # Both operations target only this application's submitted prompt.
                request('/queue', {'delete':[prompt_id]})
                request('/interrupt', {'prompt_id':prompt_id})
                check_cancel(cancel)
            history = request('/history/'+prompt_id)
            if prompt_id in history:
                result = history[prompt_id]
                if result.get('status',{}).get('status_str') != 'success':
                    raise RuntimeError('Local body generation failed. Try a shorter movement.')
                outputs = result.get('outputs',{}).get('13',{})
                items = [item for group in outputs.values() if isinstance(group,list)
                         for item in group if isinstance(item,dict) and 'filename' in item]
                if len(items) != 1:
                    raise RuntimeError('The motion worker did not return one video.')
                item = items[0]
                folder = (root/'output'/'motion').resolve()
                video = (root/'output'/item.get('subfolder','')/item['filename']).resolve()
                if video.parent != folder or not video.name.startswith(tag+'_') or video.suffix != '.mp4':
                    raise RuntimeError('The motion worker returned an unexpected output path.')
                check_cancel(cancel)
                shutil.copyfile(video,destination)
                video.unlink()
                return {'motion_s':round(time.perf_counter()-started,3), 'motion_frames':frames,
                        'motion_model':CHECKPOINT, 'motion_resolution':'384x576', 'action':action,
                        'motion_source':'fresh_diffusion','fresh_body_generation':True}
            cancel.wait(.1)
        request('/queue', {'delete':[prompt_id]})
        request('/interrupt', {'prompt_id':prompt_id})
        raise RuntimeError('Local motion took too long. Its job was stopped; you can retry.')
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise RuntimeError('Local body video is unavailable. Start scripts/start_motion.ps1 and retry.') from error
    finally:
        source.unlink(missing_ok=True)

