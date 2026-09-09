"""Compare local CPU recognizers using known, generated English speech fixtures."""
import argparse
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="asr-small")
    args=parser.parse_args()
    from faster_whisper import WhisperModel
    started=time.perf_counter()
    model=WhisperModel(str(ROOT/".cache/local-poc"/args.model),device="cpu",compute_type="int8",cpu_threads=4,num_workers=1,local_files_only=True)
    load=time.perf_counter()-started
    fixture=ROOT/"generated/local-speech"
    expected=json.loads((fixture/"benchmark.json").read_text())["samples"]
    rows=[]
    for i,item in enumerate(expected):
        started=time.perf_counter()
        segments,_=model.transcribe(str(fixture/f"sample-{i+1}.wav"),language="en",beam_size=1,vad_filter=True,condition_on_previous_text=False)
        text=" ".join(s.text.strip() for s in segments)
        elapsed=time.perf_counter()-started
        rows.append({"expected":item["text"],"transcribed":text,"seconds":elapsed})
    result={"model":args.model,"load_s":load,"scope":"Generated clear English speech; no physical mic/background-noise evaluation", "samples":rows}
    path=ROOT/f"generated/local-app/{args.model}-benchmark.json"
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
