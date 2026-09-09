"""Review live speech/lips assembled over a previously generated body benchmark.

This measures assembly only, not fresh body generation or browser playback.
Does not touch conversation, app state or the selected renderer.
"""
import json
from pathlib import Path
import sys
import threading
import time
import wave
import math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.engine import configure_runtime
from local_app.models import Models


def main():
    configure_runtime()
    models=Models()
    renderer=models.load_visual()
    renderer.prepare('fullbody')
    folder=ROOT/'generated/local-app/audit'
    audio=folder/'assembly-wave.wav'
    began=time.perf_counter()
    duration=models.speech("Hi there. Here's a wave.",audio)
    tts_s=time.perf_counter()-began
    renderer.render(audio,folder/'assembly-warm.mp4',threading.Event(),'fullbody',streaming=True)
    results=[]
    for size in ('320x480','256x384'):
        source=folder/f'direct-ltx-wave-50-{size}-73-1.mp4'
        target=folder/f'assembly-wave-{size}.mp4'
        if not source.exists():raise RuntimeError('Run and review the body benchmark first.')
        target.unlink(missing_ok=True)
        completed=threading.Event()
        first=[]
        started=time.perf_counter()
        def observe():
            while not completed.wait(.01):
                if target.exists() and target.stat().st_size>=4096:
                    first.append(time.perf_counter()-started)
                    return
        monitor=threading.Thread(target=observe,daemon=True);monitor.start()
        try:
            metrics=renderer.render(audio,target,threading.Event(),'fullbody',streaming=True,motion_path=source)
        finally:
            completed.set();monitor.join()
        result={'source':source.name,'output':target.name,'tts_s':round(tts_s,3),
                'speech_duration_s':duration,'first_4096_bytes_s':round(first[0],3) if first else None,
                'metrics':metrics,'body_generation_included':False,'browser_playback_measured':False}
        results.append(result)
        print(json.dumps(result),flush=True)
    import numpy as np
    with wave.open(str(audio),'rb') as wav:
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(np.float32)/32768
    evidence={'runs':results,'audio_peak':float(abs(samples).max()),
              'audio_rms_dbfs':20*math.log10(float(np.sqrt(np.mean(samples*samples)))+1e-12),
              'generated_speech_transcript':models.transcribe(audio.read_bytes()),
              'physical_speaker_verified':False}
    (folder/'assembly-wave.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in evidence.items() if k!='runs'}),flush=True)


if __name__=='__main__':main()
