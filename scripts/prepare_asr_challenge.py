"""Synthetic longer/corrected/paused speech; no private audio, cloud or model switch."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import socket

ROOT=Path(__file__).resolve().parents[1]
PROMPTS=[
    ('short_no','No.',True),
    ('short_stop','Stop.',False),
    ('short_wait','Wait.',False),
    ('correction','Come closer. Actually, do not come closer. Stay where you are.',True),
    ('last_negation','I was about to ask you to wave and step back, but please do not.',True),
    ('late_action','I have had quite a long day and I would like to tell you about it. Before we start, could you come closer?',False),
    ('qualified_wave','Please wave with your right hand, but do not move closer or step back.',True),
    ('memory_correction','My dog is called Maple. My cat is called Pepper. Please remember that I have two pets, and the dog is not called Pepper.',True),
    ('memory_detail','My interview is next Tuesday at nine in the morning. I am meeting my friend for lunch afterward, and I will tell you how it went when I get home.',False),
    ('long_thought','I was thinking about the conversation we had yesterday and how nervous I felt about the interview. I would like to practice what I am going to say before I leave, because I sometimes forget the first sentence when I am worried. Could you help me with that?',False),
    ('paused_negation','Please do not|wave. Just tell me what you can see.',True),
    ('paused_correction','Come closer|actually, stay there and do not move.',True),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    try:connection=socket.create_connection(('127.0.0.1',8766),timeout=.25)
    except OSError:pass
    else:connection.close();raise RuntimeError('Finish call timing before generating CPU fixtures.')
    folder=ROOT/'generated/local-app/audit'/('asr-calls-'+args.label);folder.mkdir(exist_ok=False)
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from kokoro_onnx import Kokoro
    options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
    cache=ROOT/'.cache/local-poc'
    session=ort.InferenceSession(str(cache/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    tts=Kokoro.from_session(session,str(cache/'voices-v1.0.bin'));fixtures=[]
    for voice in ['af_sarah','am_michael','bf_emma']:
        for case,prompt,negation in PROMPTS:
            parts=[]
            for part in prompt.split('|'):
                audio,rate=tts.create(part,voice=voice,speed=1,lang='en-gb' if voice.startswith('b') else 'en-us')
                if parts:parts.append(np.zeros(int(rate*.4),dtype=np.float32))
                parts.append(audio)
            audio=np.concatenate(parts)
            if not .15<=len(audio)/rate<=30:raise ValueError('Fixture exceeds the real WAV adapter duration.')
            name=voice+'-'+case;stream=io.BytesIO();sf.write(stream,audio,rate,format='WAV',subtype='PCM_16');raw=stream.getvalue()
            (folder/(name+'.wav')).write_bytes(raw)
            fixtures.append({'name':name,'case':case,'expected':prompt.replace('|',' '),'check_negation':negation,
                             'duration_s':len(audio)/rate,'sha256':hashlib.sha256(raw).hexdigest(),'condition':voice+(' + synthetic 400ms pause' if '|' in prompt else '')})
        print(json.dumps({'completed_voice':voice,'fixtures':len(fixtures)}),flush=True)
    (folder/'fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'fixtures':len(fixtures),'max_duration_s':max(r['duration_s'] for r in fixtures),'scope':'Synthesized English speech only; no real-speaker accuracy claim. Compare both baseline and candidate against these same bytes.'}))


if __name__=='__main__':main()
