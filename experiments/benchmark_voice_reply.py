"""Measure local typed-input to generated speech; excludes ASR/video/playback."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from benchmark_local import PROMPTS, reply, percentile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",default="qwen3:4b-instruct-2507-q4_K_M")
    parser.add_argument("--output-dir",type=Path,default=Path("generated/local-voice-reply"))
    parser.add_argument("--tts-threads",type=int,default=4)
    args=parser.parse_args()
    if not 0<=args.tts_threads<=16:parser.error("tts-threads must be 0..16; zero uses the runtime default")
    # Keep speech on CPU; don't silently consume the renderer's GPU allocation.
    os.environ["ONNX_PROVIDER"]="CPUExecutionProvider"
    import soundfile
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    options=ort.SessionOptions()
    options.intra_op_num_threads=args.tts_threads
    options.inter_op_num_threads=1
    session=ort.InferenceSession(".cache/local-poc/kokoro-v1.0.onnx",sess_options=options,
                                providers=["CPUExecutionProvider"])
    speech=Kokoro.from_session(session,".cache/local-poc/voices-v1.0.bin")
    reply(args.model,"Say hello in one short sentence.")
    speech.create("Hello there.",voice="af_sarah",speed=1.0,lang="en-us")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i,prompt in enumerate(PROMPTS):
        start=time.perf_counter()
        llm=reply(args.model,prompt)
        text_done=time.perf_counter()
        samples,rate=speech.create(llm["reply"],voice="af_sarah",speed=1.0,lang="en-us")
        ready=time.perf_counter()
        soundfile.write(str(args.output_dir/f"reply-{i+1}.wav"),samples,rate)
        rows.append(dict(text=llm["reply"],llm_s=text_done-start,tts_s=ready-text_done,
                         ready_s=ready-start,audio_s=len(samples)/rate))
    result=dict(measured_at=datetime.now(timezone.utc).isoformat(),model=args.model,voice="af_sarah",tts_threads=args.tts_threads,warmup=True,samples=rows,
                ready_p50_s=percentile([r["ready_s"] for r in rows],.5),
                ready_p95_s=percentile([r["ready_s"] for r in rows],.95),
                scope="Typed short prompt to complete speech waveform in memory. Sequential LLM + CPU TTS; no ASR, video, WebRTC, playback, or persistent memory app.")
    (args.output_dir/"benchmark.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
