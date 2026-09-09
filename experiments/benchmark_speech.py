"""Local Kokoro CPU speech timing; requires the isolated POC environment."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir",type=Path,default=Path(".cache/local-poc"))
    parser.add_argument("--output-dir",type=Path,default=Path("generated/local-speech"))
    args=parser.parse_args()
    import soundfile
    from kokoro_onnx import Kokoro
    start=time.perf_counter()
    speech=Kokoro(str(args.model_dir/"kokoro-v1.0.onnx"),str(args.model_dir/"voices-v1.0.bin"))
    load=time.perf_counter()-start
    args.output_dir.mkdir(parents=True,exist_ok=True)
    utterances=["How did your gardening class go today?",
                "That sounds like a pleasant way to spend the afternoon.",
                "You mentioned a piano lesson on Friday. Are you looking forward to it?",
                "What would you like to cook for dinner tonight?",
                "Welcome back. We can pick up where we left off."]
    results=[]
    for i,text in enumerate(utterances):
        start=time.perf_counter()
        samples,rate=speech.create(text,voice="af_sarah",speed=1.0,lang="en-us")
        elapsed=time.perf_counter()-start
        duration=len(samples)/rate
        soundfile.write(str(args.output_dir/f"sample-{i+1}.wav"),samples,rate)
        results.append(dict(text=text,generation_s=elapsed,audio_s=duration,
                            realtime_factor=elapsed/duration,sample_rate=rate))
    result=dict(measured_at=datetime.now(timezone.utc).isoformat(),model="Kokoro-82M ONNX v1.0",voice="af_sarah",runtime="CPU ONNX Runtime",
                load_s=load,samples=results,
                scope="Whole-utterance generation only; excludes ASR, LLM, streaming first audio, video and playback")
    (args.output_dir/"benchmark.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
