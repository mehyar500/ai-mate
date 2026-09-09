"""Measure neutral short replies through loopback Ollama; no cloud inference."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
PROMPTS = [
    "My fictional demo profile says I have a gardening class tomorrow. Ask one short follow-up question.",
    "I just finished a long walk. Reply warmly in one short sentence.",
    "I plan to cook pasta tonight. Ask one practical question in one short sentence.",
    "My fictional demo calendar has a piano lesson on Friday. Mention the event in one short sentence.",
    "I want to read for twenty minutes today. Encourage that plan in one short sentence.",
]


def post(path, payload):
    return urllib.request.urlopen(urllib.request.Request(
        OLLAMA+path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}), timeout=180)


def reply(model, prompt):
    start=time.perf_counter();first=None;sentence=None;content="";last={}
    payload={"model":model,"think":False,"stream":True,"keep_alive":"5m",
             "options":{"num_ctx":4096,"num_predict":64,"temperature":0,"seed":42},
             "messages":[{"role":"system","content":"You are a clearly identified AI in a neutral local performance test. Reply in one short sentence, at most twenty words."},
                         {"role":"user","content":prompt}]}
    with post("/api/chat",payload) as response:
        for line in response:
            event=json.loads(line);part=event.get("message",{}).get("content","")
            if part:
                if first is None:first=time.perf_counter()-start
                content+=part
                if sentence is None and any(mark in content for mark in ".!?"):
                    sentence=time.perf_counter()-start
            if event.get("done"):last=event
    if not last or not content.strip():raise RuntimeError("Ollama did not complete a visible reply")
    if last.get("done_reason")=="length" or len(content.split())>35:
        raise RuntimeError("Reply failed the bounded short-answer check; do not report it as successful call latency")
    duration=last.get("eval_duration",0)/1e9
    return dict(first_token_s=first,first_sentence_s=sentence,total_s=time.perf_counter()-start,
                output_tokens=last.get("eval_count",0),input_tokens=last.get("prompt_eval_count",0),
                tokens_per_second=last.get("eval_count",0)/duration if duration else None,
                model_load_s=last.get("load_duration",0)/1e9,reply=content)


def percentile(values,q):
    ordered=sorted(values)
    return ordered[max(0,math.ceil(q*len(ordered))-1)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",default="qwen3:4b-instruct-2507-q4_K_M")
    parser.add_argument("--samples",type=int,default=10)
    parser.add_argument("--output",type=Path,default=Path("generated/local-benchmark.json"))
    args=parser.parse_args()
    if not 1<=args.samples<=50:parser.error("samples must be 1..50")
    # Unload only the explicitly selected test model. Other local model settings
    # and saved model definitions are not changed.
    with post("/api/generate",{"model":args.model,"keep_alive":0}):pass
    cold=reply(args.model,PROMPTS[0])
    samples=[reply(args.model,PROMPTS[i%len(PROMPTS)]) for i in range(args.samples)]
    metrics={}
    for key in ("first_token_s","first_sentence_s","total_s","tokens_per_second"):
        values=[s[key] for s in samples if s[key] is not None]
        metrics[key]={"p50":percentile(values,.5),"p95":percentile(values,.95)} if values else None
    gpu=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total,memory.used,driver_version",
                        "--format=csv,noheader"],capture_output=True,text=True,check=True).stdout.strip()
    with urllib.request.urlopen(OLLAMA+"/api/ps",timeout=10) as response:
        residents=json.load(response)
    result=dict(measured_at=datetime.now(timezone.utc).isoformat(),model=args.model,context_tokens=4096,sample_count=len(samples),
                test_scope="Neutral short-reply local LLM only; not audio, video, adult quality, or end-to-end call latency",
                cold=cold,warm=metrics,samples=samples,gpu_snapshot=gpu,resident_models=residents)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("model","sample_count","cold","warm","gpu_snapshot")},indent=2))
    print("Detailed local results:",args.output)


if __name__=="__main__":main()
