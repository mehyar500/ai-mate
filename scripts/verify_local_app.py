"""Exercise a running local app with synthetic test data; intentionally resets it.

Only run against an unused test/demo instance. No real microphone recording.
"""
import argparse
import io
import json
from pathlib import Path
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--reset-demo", action="store_true", required=True)
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    bootstrap = json.load(urllib.request.urlopen(base + "/api/bootstrap"))
    token = bootstrap["token"]

    def request(path, body=None, raw=None, headers=None):
        meta = {"X-Local-Token": token}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            meta["Content-Type"] = "application/json"
        if raw is not None:
            payload = raw
        meta.update(headers or {})
        req = urllib.request.Request(base+path, data=payload, headers=meta)
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)

    def wait(key, limit=600):
        start = time.perf_counter()
        while time.perf_counter()-start < limit:
            job = request("/api/jobs/" + key)
            if job["state"] in {"done", "failed", "cancelled"}:
                return job
            time.sleep(.15)
        request("/api/cancel", {"id": key})
        raise TimeoutError("Local job exceeded test timeout")

    if not bootstrap["ready"]:
        raise RuntimeError("Local server is not ready.")
    request("/api/reset", {})
    request("/api/memory", {"memory": "My name is Alex. My piano lesson is on Friday. I enjoy gardening."})
    rows = []
    prompts = ["What is my name and when is my piano lesson?", "I planted tomatoes today. Ask me one short question about them.", "I had a tiring day. Could we take a quiet moment?"]
    for prompt in prompts:
        key = request("/api/turn", {"text": prompt, "mode": "voice", "scene": "mira"})["id"]
        job = wait(key)
        if job["state"] != "done":
            raise RuntimeError(job)
        rows.append(job)
        print(json.dumps({"kind": "voice", "text": job["text"], "metrics": job["metrics"]}), flush=True)
    assert "Alex" in rows[0]["text"] and "Friday" in rows[0]["text"], "Memory recall needs refinement"
    # ASR fixture is generated speech, not evidence of real-microphone quality.
    import sys
    sys.path.insert(0, str(ROOT))
    from local_app.models import CACHE
    from kokoro_onnx import Kokoro
    import onnxruntime as ort
    import soundfile as sf
    options = ort.SessionOptions(); options.intra_op_num_threads=4; options.inter_op_num_threads=1
    session = ort.InferenceSession(str(CACHE/"kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    tts = Kokoro.from_session(session, str(CACHE/"voices-v1.0.bin"))
    audio, rate = tts.create("What day is my piano lesson?", voice="af_sarah", speed=1, lang="en-us")
    buffer = io.BytesIO(); sf.write(buffer, audio, rate, format="WAV", subtype="PCM_16")
    key = request("/api/audio", raw=buffer.getvalue(), headers={"Content-Type":"audio/wav", "X-Reply-Mode":"voice"})["id"]
    job = wait(key); rows.append(job)
    assert job["state"] == "done", job
    print(json.dumps({"kind":"asr_fixture", "transcript":job["user"], "text":job["text"], "metrics":job["metrics"]}), flush=True)
    if args.video:
        prompts = ["Say hello in one brief sentence.", "What should I do before my piano lesson?", "Ask me a short question about my garden."]
        for scene, prompt in zip(["mira", "garden", "cafe"], prompts):
            key=request("/api/turn", {"text":prompt,"mode":"video","scene":scene})["id"]
            job=wait(key); rows.append(job)
            job["tested_scene"] = scene
            print(json.dumps({"kind":"video", "text":job["text"], "metrics":job["metrics"], "state":job["state"], "error":job["error"], "chunks":job["chunks"]}), flush=True)
            assert job["state"] == "done", job
    result={"scope":"Local app synthetic HTTP trials. ASR uses a generated voice fixture, not a physical microphone. Small sample; no full-call latency claim.", "jobs":rows}
    if args.video:
        before = request("/api/status")["turns"]
        key = request("/api/turn", {"text":"Suggest a calm activity in one short sentence.", "mode":"video", "scene":"mira"})["id"]
        deadline = time.perf_counter()+30
        while request("/api/jobs/"+key)["state"] != "rendering":
            if time.perf_counter() > deadline:
                request("/api/cancel", {"id":key})
                raise TimeoutError("Could not observe rendering for the cancellation trial")
            time.sleep(.02)
        started = time.perf_counter()
        request("/api/cancel", {"id":key})
        cancelled = wait(key)
        assert cancelled["state"] == "cancelled", cancelled
        assert request("/api/status")["turns"] == before, "Cancelled reply was persisted"
        # The worker may still be removing its files immediately after state changes.
        while request("/api/status")["busy"]:
            time.sleep(.02)
        assert not list((ROOT/"generated/local-app").glob(key+"-*")), "Cancelled media remains"
        result["cancellation"] = {"state":"cancelled", "observed_phase":"rendering", "seconds":time.perf_counter()-started, "memory_unchanged":True, "reply_media_removed":True}
        print(json.dumps(result["cancellation"]), flush=True)
    path=ROOT/"generated/local-app/integration-results.json"
    path.write_text(json.dumps(result,indent=2))
    print(f"Evidence: {path}")


if __name__ == "__main__":
    main()
