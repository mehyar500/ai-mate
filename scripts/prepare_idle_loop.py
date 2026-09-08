"""Prepare an already reviewed, non-explicit full-body listening clip for local use."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--pose',choices=['base','near'],default='base')
    parser.add_argument('--candidate',action='store_true',help='Write to audit for review without replacing active footage.')
    args = parser.parse_args()
    source = args.source.resolve()
    allowed = [ROOT/'.cache/local-poc/ComfyUI/output/motion', ROOT/'generated/local-app/audit']
    if source.parent not in [p.resolve() for p in allowed] or source.suffix != '.mp4':
        parser.error('Use a reviewed local benchmark MP4.')
    probe = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                            'stream=duration,width,height','-of','json',str(source)],
                           capture_output=True,check=True,timeout=10)
    video = json.loads(probe.stdout)['streams'][0]
    duration = float(video['duration'])
    if not 2 <= duration <= 8 or (video['width'],video['height']) != (384,576):
        parser.error('The reviewed loop must be 384x576 and 2–8 seconds.')
    folder = ROOT/'generated/local-app'
    name='fullbody' if args.pose=='base' else 'near'
    reference=folder/('fullbody.png' if args.pose=='base' else 'performance-near.png')
    out = (folder/'audit'/f'idle-{name}-candidate.mp4') if args.candidate else folder/f'idle-{name}.mp4'
    out.parent.mkdir(exist_ok=True)
    # Join the final quarter-second to the first; start at that first quarter's end.
    transition = .25
    graph = (f'[0:v]split[a][b];[a]trim=start={transition},setpts=PTS-STARTPTS[main];'
             f'[b]trim=end={transition},setpts=PTS-STARTPTS[head];'
             f'[main][head]xfade=transition=fade:duration={transition}:offset={duration-2*transition}[v]')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-filter_complex_threads','2',
                    '-filter_complex',graph,'-map','[v]','-an','-c:v','libx264','-preset','fast',
                    '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True,timeout=30)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {'version':1,'scene':'fullbody','pose':args.pose,'model':'LTX-2.3-22B-distilled-FP8',
                'source_sha256':sha(source),'reference_sha256':sha(reference),
                'sha256':sha(out),'precomputed':True,'audio':False}
    out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(out),'sha256':manifest['sha256'],'requires_output_review':True}))


if __name__ == '__main__':
    main()
