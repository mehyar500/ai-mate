"""Non-destructive local streaming cancellation check; no conversation reset."""
import json
from pathlib import Path
import time
import urllib.request


def main():
    base="http://127.0.0.1:8765"
    with urllib.request.urlopen(base+"/api/bootstrap",timeout=5) as response:
        initial=json.load(response)
    if not initial["ready"] or initial["busy"]:
        raise SystemExit("Wait for an idle ready server.")
    token=initial["token"]
    def request(path,body=None):
        data=None if body is None else json.dumps(body).encode()
        headers={"X-Local-Token":token,"Content-Type":"application/json"}
        with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=10) as response:
            return json.load(response)
    started=time.perf_counter()
    key=request("/api/turn",{"text":"In a video reply, give me two short sentences about growing tomatoes in a small garden.","mode":"video","scene":"garden"})["id"]
    try:
        for _ in range(300):
            job=request("/api/jobs/"+key)
            if job["chunks"]:break
            if job["state"] in {"failed","cancelled","done"}:raise RuntimeError("No streaming media: "+job["state"])
            time.sleep(.1)
        stream=job["chunks"][0]["stream"]
        with urllib.request.urlopen(urllib.request.Request(base+stream,headers={"X-Local-Token":token}),timeout=15) as response:
            first=response.read(4096)
            first_byte_s=time.perf_counter()-started
            before=request("/api/jobs/"+key)
            assert first and before["state"]=="rendering", "Video was not delivered while rendering"
            cancelled=time.perf_counter()
            request("/api/cancel",{"id":key})
        for _ in range(100):
            result=request("/api/jobs/"+key)
            if result["state"]=="cancelled":break
            time.sleep(.05)
        assert result["state"]=="cancelled",result["state"]
        state=request("/api/status")
        assert state["turns"]==initial["turns"],"Cancellation changed conversation"
        assert state["memory"]==initial["memory"],"Cancellation changed notes"
        assert state.get("facts",[])==initial.get("facts",[]),"Cancellation saved facts"
        files=list(Path("generated/local-app").glob(key+"-*"))
        assert not files,"Cancelled media was retained"
        evidence={"first_4096_bytes_s":round(first_byte_s,3),"state_when_bytes_arrived":before["state"],
                  "cancel_s":round(time.perf_counter()-cancelled,3),"conversation_unchanged":True,"media_removed":True}
        Path("generated/local-app/audit").mkdir(parents=True,exist_ok=True)
        Path("generated/local-app/audit/stream-cancel.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
        print(json.dumps(evidence,indent=2))
    finally:
        request("/api/cancel",{"id":key})


if __name__=="__main__":main()
