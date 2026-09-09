"""Bounded synthetic Cloudflare speech comparison; does not select a new voice.

Uses the existing explicitly configured API-key/email or token flow. No private
conversation is read, sent or logged. Maximum six short requests per invocation.
"""
import io
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app.engine import configure_runtime
from local_app.conversation import Conversation

MODEL='@cf/deepgram/aura-2-en'
CASES={
    'short':'Let me try that.',
    'normal':'The garden is quiet with birdsong. Flowers sway in the breeze.',
    'long':'One, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, twenty, twenty-one, twenty-two, twenty-three, twenty-four, twenty-five.',
}


def main():
    configure_runtime()
    auth=Conversation('unused')
    if auth.provider!='cloudflare':
        raise SystemExit('This benchmark requires the existing Cloudflare configuration.')
    folder=ROOT/'generated/local-app/audit'
    folder.mkdir(exist_ok=True)
    results=[]
    for repeat in range(2):
        for name,text in CASES.items():
            body={'text':text,'speaker':'luna','encoding':'linear16','container':'wav','sample_rate':24000}
            request=urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{auth.account}/ai/run/{MODEL}',
                data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**auth.cf_headers})
            start=time.perf_counter()
            try:
                with urllib.request.urlopen(request,timeout=30) as response:
                    first=response.read(4096)
                    first_s=time.perf_counter()-start
                    audio=first+response.read(2_000_001)
                    content_type=response.headers.get('Content-Type')
                if len(audio)>2_000_000:
                    raise ValueError('Audio exceeds the synthetic benchmark limit.')
                with wave.open(io.BytesIO(audio),'rb') as wav:
                    rate=wav.getframerate()
                    if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or rate!=24000:
                        raise ValueError('Unexpected audio format.')
                    # Streamed WAV headers can use an unknown-length sentinel.
                    pcm=wav.readframes(rate*31)
                    duration=len(pcm)/(rate*2)
                    if not .1<duration<=30:
                        raise ValueError('Unexpected audio duration.')
                elapsed=time.perf_counter()-start
                out=folder/f'cloud-aura-{name}-{repeat}.wav'
                with wave.open(str(out),'wb') as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm)
                result={'case':name,'repeat':repeat,'model':MODEL,'speaker':'luna','first_4096_bytes_s':round(first_s,3),
                        'complete_s':round(elapsed,3),'audio_s':duration,'characters':len(text),
                        'list_price_usd':round(len(text)*.03/1000,6),'content_type':content_type}
            except urllib.error.HTTPError as error:
                result={'case':name,'repeat':repeat,'error':'HTTP '+str(error.code)}
            except (ValueError,wave.Error,OSError) as error:
                result={'case':name,'repeat':repeat,'error':type(error).__name__}
            results.append(result)
            print(json.dumps(result),flush=True)
            (folder/'cloud-speech-benchmark.json').write_text(json.dumps(results,indent=2)+'\n')
            if 'error' in result:
                return  # No automatic retry of a failed paid request.


if __name__=='__main__':
    main()
