"""Synthetic speech/render comparison; never reads or writes conversation state."""
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.engine import configure_runtime
from local_app.models import Models


def main():
    configure_runtime()
    models=Models()
    renderer=models.load_visual()
    folder=ROOT/'generated/local-app/audit'
    audio=folder/'listening-timing.wav'
    source=ROOT/'generated/local-app/idle-fullbody.mp4'
    start=time.perf_counter()
    speech_duration=models.speech('Hello there.',audio)
    speech_s=time.perf_counter()-start
    renderer.prepare('fullbody')
    renderer.render(audio,folder/'listening-timing-warm.mp4',threading.Event(),'fullbody',streaming=True)
    rows=[]
    for name,loop in [('old-padding-equivalent',False),('speech-duration',True),('speech-duration-warm',True)]:
        target=folder/f'listening-{name}.mp4';target.unlink(missing_ok=True)
        done=threading.Event();first=[];start=time.perf_counter()
        def observe():
            while not done.wait(.01):
                if target.exists() and target.stat().st_size>=4096:
                    first.append(time.perf_counter()-start);return
        watcher=threading.Thread(target=observe,daemon=True);watcher.start()
        try:
            metrics=renderer.render(audio,target,threading.Event(),'fullbody',streaming=True,
                motion_path=source,loop_motion=loop,reuse_motion=True)
        finally:
            done.set();watcher.join()
        row={'case':name,'speech_s':round(speech_s,3),'speech_duration_s':speech_duration,
            'first_render_4096_bytes_s':round(first[0],3) if first else None,'render':metrics}
        rows.append(row);print(json.dumps(row),flush=True)
    result={'scope':'Same synthetic WAV; assembly timing excludes LLM, ASR and browser playback.',
        'source':'idle-fullbody.mp4','samples':rows,
        'asr_recovered':models.transcribe(audio.read_bytes()),'physical_speaker_verified':False}
    (folder/'listening-timing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'asr_recovered':result['asr_recovered']}),flush=True)


if __name__=='__main__':
    main()
