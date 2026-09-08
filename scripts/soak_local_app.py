"""Timed synthetic local conversation; requires explicit disposable-demo reset."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds",type=int,default=600)
    parser.add_argument("--interval",type=int,default=15)
    parser.add_argument("--mode",choices=["text","voice","video"],default="voice")
    parser.add_argument("--reset-demo",action="store_true",required=True)
    args=parser.parse_args()
    if not 30<=args.seconds<=1800 or not 1<=args.interval<=60:parser.error("Invalid test duration/interval")
    base="http://127.0.0.1:8765"
    token=json.load(urllib.request.urlopen(base+"/api/bootstrap"))["token"]
    def api(path,body=None):
        headers={"X-Local-Token":token}
        raw=None
        if body is not None:raw=json.dumps(body).encode();headers["Content-Type"]="application/json"
        with urllib.request.urlopen(urllib.request.Request(base+path,data=raw,headers=headers),timeout=45) as response:return json.load(response)
    api("/api/reset",{})
    api("/api/memory",{"memory":"My name is Alex. My piano lesson is Friday. I like gardening and cooking. My dog is named Maple."})
    prompts=["What is my dog's name?","I tried a new soup recipe today. Ask one short question about it.","What is my next lesson?","Suggest one simple thing I could do in my garden.","I have ten minutes free. What could I practice?","What name should you call me?","Let's have a short, quiet conversation.","What were the hobbies I asked you to remember?"]
    rows=[]; started=time.perf_counter(); deadline=started+args.seconds
    while time.perf_counter()<deadline:
        turn_started=time.perf_counter()
        key=api("/api/turn",{"text":prompts[len(rows)%len(prompts)],"mode":args.mode,"scene":"mira"})["id"]
        while True:
            row=api("/api/jobs/"+key)
            if row["state"] in {"done","failed","cancelled"}:break
            if time.perf_counter()-turn_started>180:
                api("/api/cancel",{"id":key});raise TimeoutError("Stuck turn")
            time.sleep(.15)
        gpu=subprocess.run(["nvidia-smi","--query-gpu=memory.used","--format=csv,noheader,nounits"],capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        row["device_memory_snapshot_mib"]=gpu.stdout.strip()
        rows.append(row)
        print(json.dumps({"turn":len(rows),"state":row["state"],"metrics":row["metrics"],"text":row["text"]}),flush=True)
        if row["state"]!="done":raise RuntimeError(row["error"])
        path=ROOT/f"generated/local-app/soak-{args.mode}.json"
        path.write_text(json.dumps({"mode":args.mode,"elapsed_s":time.perf_counter()-started,"scope":"Synthetic typed HTTP turns; no microphone or browser playback. GPU values are between-turn snapshots, not instrumented peaks.","jobs":rows},indent=2))
        time.sleep(max(0,min(deadline-time.perf_counter(),args.interval-(time.perf_counter()-turn_started))))
    print(f"Completed {len(rows)} turns over {time.perf_counter()-started:.1f} seconds.")


if __name__=="__main__":main()
