"""Profile synthetic GPU recognition before/after loading the actual renderer."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--blas-threads',type=int,choices=[1,4,8])
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}',args.label):parser.error('Use a short lowercase label.')
    if args.blas_threads is not None:os.environ['OPENBLAS_NUM_THREADS']=str(args.blas_threads)
    from local_app.engine import configure_runtime
    from local_app.models import Models
    configure_runtime();os.environ['AI_MATE_ASR_DEVICE']='cuda';os.environ['AI_MATE_VISUAL_DECODER']='tensorrt'
    folder=ROOT/'generated/local-app/audit'/('asr-runtime-'+args.label);folder.mkdir(exist_ok=False)
    model=Models()
    raw=(ROOT/'generated/local-app/audit/voice-video-qualification-speech-continuity/greeting.wav').read_bytes()
    # Import the module explicitly: some library versions export a same-named function.
    import importlib
    api=importlib.import_module('faster_whisper.transcribe')
    original_extract=model.asr.feature_extractor;original_encode=model.asr.encode
    stages={};rows=[]
    def timed(key,fn):
        def call(*values,**options):
            start=time.perf_counter();result=fn(*values,**options);stages[key]=time.perf_counter()-start;return result
        return call
    class Extract:
        def __getattr__(self,name):return getattr(original_extract,name)
        def __call__(self,*values,**options):return timed('features_s',original_extract)(*values,**options)
    model.asr.feature_extractor=Extract();model.asr.encode=timed('encode_s',original_encode)
    with patch.object(api,'decode_audio',timed('audio_decode_s',api.decode_audio)),patch.object(api,'get_speech_timestamps',timed('vad_s',api.get_speech_timestamps)):
        for phase in ['models_only','renderer_loaded','after_pause']:
            if phase=='renderer_loaded':model.load_visual().prepare('fullbody')
            if phase=='after_pause':time.sleep(5)
            for index in range(3):
                stages.clear();start=time.perf_counter();text=model.transcribe(raw)
                row={'phase':phase,'index':index,'seconds':time.perf_counter()-start,'text':text,**stages};rows.append(row)
                print(json.dumps(row),flush=True)
                (folder/'results.json').write_text(json.dumps({'blas_threads_override':args.blas_threads,
                    'scope':'Fixed synthetic greeting; actual Models and selected renderer loaded, no cloud inference or private inputs. Component wrappers preserve arguments. Five-second pause probes idle recovery; not a call benchmark.',
                    'rows':rows},indent=2)+'\n')


if __name__=='__main__':main()
