"""Compare official float/int8 Kokoro files on CPU with the same utterances."""
import argparse
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filename",default="kokoro-v1.0.int8.onnx")
    args=parser.parse_args()
    import onnxruntime as ort
    import soundfile as sf
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
    cache=ROOT/".cache/local-poc"
    options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(cache/args.filename),sess_options=options,providers=["CPUExecutionProvider"])
    voice=Kokoro.from_session(session,str(cache/"voices-v1.0.bin"))
    asr=WhisperModel(str(cache/"asr-base-en"),device="cpu",compute_type="int8",cpu_threads=4,local_files_only=True)
    texts=["Your name is Alex.","Your piano lesson is on Friday.","Try planting a few herbs like mint or basil. They grow easily and smell great.","What kind of soup did you make?","We can take a quiet moment together."]
    output=ROOT/"generated/local-app"/args.filename.replace(".onnx","")
    output.mkdir(exist_ok=True)
    voice.create("Hello there.",voice="af_sarah",speed=1,lang="en-us")
    rows=[]
    for i,text in enumerate(texts):
        started=time.perf_counter();audio,rate=voice.create(text,voice="af_sarah",speed=1,lang="en-us");elapsed=time.perf_counter()-started
        path=output/f"sample-{i}.wav";sf.write(str(path),audio,rate)
        segments,_=asr.transcribe(str(path),language="en",beam_size=1,vad_filter=True)
        rows.append({"text":text,"seconds":elapsed,"duration_s":len(audio)/rate,"transcribed":" ".join(s.text.strip() for s in segments)})
    result={"model":args.filename,"scope":"Sequential CPU timing and ASR round-trip; not a subjective listening test", "samples":rows}
    (output/"benchmark.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
