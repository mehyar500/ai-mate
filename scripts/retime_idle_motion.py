"""Retime reviewed photographic idle footage without replacing its person/background.

The operator selects an observed bilateral blink interval. Normal movement slows;
that interval is compressed separately. Output is an unreviewed candidate only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--blink-start',type=float,required=True)
    parser.add_argument('--blink-end',type=float,required=True)
    parser.add_argument('--blink-seconds',type=float,default=.25)
    parser.add_argument('--speed',type=float,default=.5)
    args=parser.parse_args()
    source=args.source.resolve()
    roots=[ROOT/'generated/local-app',ROOT/'.cache/local-poc/ComfyUI/output/motion']
    if source.suffix!='.mp4' or not any(source.is_relative_to(p.resolve()) for p in roots):
        parser.error('Use reviewed app/benchmark footage.')
    probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=duration,width,height','-of','json',str(source)],capture_output=True,check=True,timeout=10)
    video=json.loads(probe.stdout)['streams'][0]
    duration=float(video['duration'])
    start,end=args.blink_start,args.blink_end
    if ((video['width'],video['height'])!=(384,576) or not 2<=duration<=8
            or not 0<start<end<duration or not .4<=args.speed<=1
            or not .1<=args.blink_seconds<=.4):
        parser.error('Use 384x576 short footage, a valid blink interval, speed 0.4–1 and blink 0.1–0.4s.')
    target=(duration-(end-start))/args.speed+args.blink_seconds
    if target>6:
        parser.error('Keep the retimed clip within the 144-frame appearance-cache limit (6 seconds).')
    before=start/args.speed
    expression=(f'if(lt(T,{start}),T/{args.speed},'
        f'if(lt(T,{end}),{before}+(T-{start})*{args.blink_seconds}/{end-start},'
        f'{before+args.blink_seconds}+(T-{end})/{args.speed}))/TB')
    folder=ROOT/'generated/local-app/audit';folder.mkdir(exist_ok=True)
    out=folder/(source.stem+'-retimed.mp4')
    # Optical-flow interpolation smooths the slowed sections of the full frame.
    # There is no independently translated/animated face or body cutout.
    graph=f"setpts='{expression}',minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1"
    subprocess.run(['ffmpeg','-hide_banner','-v','error','-y','-i',str(source),'-an',
        '-vf',graph,'-filter_threads','2','-c:v','libx264','-threads','2','-preset','fast',
        '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True,timeout=90)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result={'source_sha256':sha(source),'output_sha256':sha(out),'output':str(out),
        'source_duration_s':duration,'blink_source_interval_s':[start,end],
        'target_blink_s':args.blink_seconds,'normal_playback_speed':args.speed,
        'filter':graph,'requires_output_review':True}
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
