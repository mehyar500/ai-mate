"""Run with python -m local_app.server. Binds only to 127.0.0.1."""
import argparse
import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import urlparse
import uuid

from .core import Store, messages_for
from .models import Cancelled, Models, ROOT, check_cancel

WEB = ROOT / "local_app/web"
MEDIA = ROOT / "generated/local-app"


class Application:
    def __init__(self, directory=MEDIA, model_factory=Models):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.directory / "memory.sqlite3")
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.jobs = {}
        self.busy = False
        self.models = None
        self.ready = False
        self.error = None
        self.visual_error = None
        self.startup_s = None
        self.factory = model_factory
        self.scene = self.store.current_scene()

    def warm(self):
        started = time.perf_counter()
        try:
            self.models = self.factory()
            event = threading.Event()
            self.models.plan({"memory": "", "turns": []}, "Say hello briefly.", "auto", "mira", ["mira"], event)
            if (self.directory/"mira.png").exists():
                try:
                    renderer = self.models.load_visual()
                    renderer.prepare("mira")
                    warm_audio = ROOT/".cache/local-poc/renderer-warm.wav"
                    self.models.speech("Hello there.", warm_audio)
                    renderer.render(warm_audio, warm_audio.with_suffix(".mp4"), event)
                except Exception as error:
                    self.visual_error = "Video warm-up failed. Voice and text remain available; check the terminal."
                    print(f"Video startup error: {type(error).__name__}: {error}", flush=True)
            self.ready = True
            self.startup_s = round(time.perf_counter()-started, 3)
            print(f"Local dialogue, speech and microphone models are ready in {self.startup_s}s.", flush=True)
        except Exception as error:
            self.error = "Local model startup failed. Check the terminal and model setup."
            print(f"Startup error: {type(error).__name__}: {error}", flush=True)

    def status(self):
        with self.lock:
            return {"app_version": "0.2", "ready": self.ready, "error": self.error, "busy": self.busy,
                    "startup_s": self.startup_s,
                    "visual_loaded": bool(self.models and self.models.visual is not None and self.visual_error is None),
                    "visual_error": self.visual_error,
                    "scene": self.scene,
                    "provider": getattr(getattr(self.models, "conversation", None), "provider", "ollama"),
                    "scenes": [s for s in ["mira", "garden", "cafe"] if (self.directory / (s+".png")).exists()],
                    **self.store.snapshot()}

    def submit(self, text, mode, scene, raw=None):
        if mode not in {"auto", "text", "voice", "video"}:
            raise ValueError("Select text, voice or video.")
        if scene not in {"auto", "mira", "garden", "cafe"}:
            raise ValueError("Unknown scene.")
        if raw is None and (not isinstance(text, str) or not text.strip() or len(text) > 1000):
            raise ValueError("Enter a message between 1 and 1,000 characters.")
        with self.lock:
            if not self.ready:
                raise RuntimeError("The local models are still loading or unavailable.")
            if self.busy:
                raise BlockingIOError("One reply is already running. Stop it or wait.")
            self.busy = True
            key = uuid.uuid4().hex
            event = threading.Event()
            self.jobs[key] = {"id": key, "state": "transcribing" if raw else "thinking", "text": "", "user": text,
                              "chunks": [], "metrics": {}, "cancel": event, "error": None}
            while len(self.jobs) > 20:
                self.jobs.pop(next(iter(self.jobs)))
            threading.Thread(target=self.run, args=(key, text, mode, scene, raw), daemon=True).start()
            return key

    def job(self, key):
        with self.lock:
            if key not in self.jobs:
                raise KeyError("Reply not found.")
            return copy.deepcopy({k: v for k, v in self.jobs[key].items() if k != "cancel"})

    def cancel(self, key=None):
        with self.lock:
            for job_id, job in self.jobs.items():
                if key is None or key == job_id:
                    job["cancel"].set()

    def reset(self):
        with self.lock:
            self.cancel()
            self.store.reset()
            self.scene = "mira"
            # In-flight files belong to the cancelling worker. Also clear replies
            # from previous process lifetimes, whose jobs are no longer in RAM.
            active_keys = {job["id"] for job in self.jobs.values()
                           if job["state"] not in {"done", "failed", "cancelled"}}
            for path in self.directory.iterdir():
                if re.fullmatch(r"[a-f0-9]{32}-\d+\.(wav|mp4)", path.name):
                    if path.name.split("-", 1)[0] not in active_keys:
                        path.unlink(missing_ok=True)
            self.jobs = {k: v for k, v in self.jobs.items() if v["state"] not in {"done", "failed", "cancelled"}}

    def remove_media(self, key):
        for path in self.directory.glob(key + "-*"):
            if path.suffix in {".wav", ".mp4"}:
                path.unlink(missing_ok=True)

    def run(self, key, text, mode, scene, raw):
        job = self.jobs[key]
        event = job["cancel"]
        started = time.perf_counter()
        try:
            if raw is not None:
                text = self.models.transcribe(raw)
                check_cancel(event)
                if not text:
                    raise ValueError("No speech detected. Try again or type a message.")
                if len(text) > 1000:
                    raise ValueError("Recording was too long. Try a shorter message.")
                with self.lock:
                    job["user"] = text
                    job["metrics"]["asr_s"] = round(time.perf_counter()-started, 3)
            scene = self.scene if scene == "auto" else scene
            plan = None
            if hasattr(self.models, "plan"):
                available = [s for s in ("mira", "garden", "cafe") if (self.directory/(s+".png")).exists()]
                plan = self.models.plan(self.store.snapshot(), text, mode, scene, available, event)
                check_cancel(event)
                mode, scene = plan["presentation"], plan["scene"]
                with self.lock:
                    job["presentation"], job["scene"] = mode, scene
                    job["text"] = plan["reply"]
                    job["metrics"]["first_text_s"] = round(time.perf_counter()-started, 3)
                    if mode == "portrait":
                        job["portrait"] = "/portrait/" + scene + ".png"
                if mode == "portrait":
                    mode = "text"
            if mode == "video":
                with self.lock:
                    job["state"] = "warming_video"
                renderer = self.models.load_visual()
                renderer.prepare(scene)
                check_cancel(event)
            with self.lock:
                job["state"] = "thinking"
            parts = []
            phrases = [plan["reply"]] if plan else self.models.stream_reply(messages_for(self.store.snapshot(), text), event)
            for phrase in phrases:
                check_cancel(event)
                parts.append(phrase)
                with self.lock:
                    job["text"] = " ".join(parts)
                    job["metrics"].setdefault("first_text_s", round(time.perf_counter()-started, 3))
                    job["state"] = "speaking" if mode != "text" else "thinking"
                if mode != "text":
                    index = len(parts) - 1
                    filename = f"{key}-{index}"
                    audio_path = self.directory / (filename + ".wav")
                    audio_duration = self.models.speech(phrase, audio_path)
                    check_cancel(event)
                    chunk = {"index": index, "text": phrase, "audio": "/media/"+filename+".wav", "duration_s": audio_duration}
                    if mode == "video":
                        chunk["video"] = "/media/"+filename+".mp4"
                        chunk["stream"] = "/api/streams/"+filename+".mp4"
                        with self.lock:
                            job["state"] = "rendering"
                            job["chunks"].append(chunk)
                        metrics = renderer.render(audio_path, self.directory / (filename+".mp4"), event, scene, streaming=True)
                        chunk["render"] = metrics
                    check_cancel(event)
                    with self.lock:
                        if mode != "video":
                            job["chunks"].append(chunk)
                        job["metrics"].setdefault("first_media_ready_s", round(time.perf_counter()-started, 3))
                if len(parts) >= 2:
                    break
            if not parts:
                raise RuntimeError("The model did not return a complete reply. Please retry.")
            with self.lock:
                check_cancel(event)
                self.store.append(text, " ".join(parts))
                if plan:
                    self.store.learn(plan["facts"])
                    job["remembered"] = plan["facts"]
                self.scene = scene
                self.store.set_scene(scene)
                job["metrics"]["total_s"] = round(time.perf_counter()-started, 3)
                job["state"] = "done"
        except Cancelled:
            with self.lock:
                job["state"] = "cancelled"
                job["chunks"] = []
                job["user"] = ""
                job["text"] = ""
            self.remove_media(key)
        except Exception as error:
            with self.lock:
                job["state"] = "failed"
                job["error"] = str(error) if isinstance(error, (ValueError, RuntimeError)) else "Local inference failed. Check the terminal; you can retry."
                if isinstance(error, ValueError) and str(error).startswith("No speech detected."):
                    job["error_code"] = "no_speech"
            # Third-party exception messages can contain supplied text. Keep
            # details in the local job response, never in persistent logs.
            print(f"Reply failed: {type(error).__name__}", flush=True)
        finally:
            with self.lock:
                self.busy = False
            # Bound generated media growth. Keep the latest 100 files, never scene assets.
            files = sorted([p for p in self.directory.iterdir() if re.fullmatch(r"[a-f0-9]{32}-\d+\.(wav|mp4)", p.name)], key=lambda p: p.stat().st_mtime)
            for path in files[:-100]:
                path.unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "AI-mate-local"

    def log_message(self, format, *args):
        # Do not put user messages, transcripts or tokens in the server log.
        pass

    @property
    def app(self):
        return self.server.app

    def allowed(self, mutate=False):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            self.respond(403, {"error": "Loopback Host required."})
            return False
        origin = self.headers.get("Origin")
        if (origin and origin not in {"http://"+host for host in allowed}) or self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.respond(403, {"error": "Same-origin requests only."})
            return False
        if mutate and not secrets.compare_digest(self.headers.get("X-Local-Token", ""), self.app.token):
            self.respond(403, {"error": "Reload the local app before continuing."})
            return False
        return True

    def respond(self, status, content, mime="application/json", head=False, extra=None):
        data = json.dumps(content).encode() if mime == "application/json" else content
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        if not head:
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        if not self.allowed():
            return
        path = urlparse(self.path).path
        static = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript"),
                  "/style.css": ("style.css", "text/css"), "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
                  "/icon.svg": ("icon.svg", "image/svg+xml"), "/recorder.js": ("recorder.js", "text/javascript")}
        if path in static:
            file, mime = static[path]
            return self.respond(200, (WEB / file).read_bytes(), mime)
        if path == "/api/bootstrap":
            return self.respond(200, {"token": self.app.token, **self.app.status()})
        if path in {"/portrait/mira.png", "/portrait/garden.png", "/portrait/cafe.png"}:
            file = self.app.directory / path.rsplit("/", 1)[-1]
            if file.exists():
                return self.respond(200, file.read_bytes(), "image/png")
        if re.fullmatch(r"/media/[a-f0-9]{32}-\d+\.(wav|mp4)", path):
            file = self.app.directory / path.rsplit("/", 1)[-1]
            if file.exists():
                data = file.read_bytes()
                mime = "video/mp4" if file.suffix == ".mp4" else "audio/wav"
                requested = self.headers.get("Range")
                if requested:
                    match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                    if not match or int(match[1]) >= len(data):
                        return self.respond(416, b"", mime, extra={"Content-Range": f"bytes */{len(data)}"})
                    start, end = int(match[1]), min(int(match[2]) if match[2] else len(data)-1, len(data)-1)
                    if end < start:
                        return self.respond(416, b"", mime)
                    return self.respond(206, data[start:end+1], mime, extra={"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{len(data)}"})
                return self.respond(200, data, mime, extra={"Accept-Ranges": "bytes"})
        if path.startswith("/api/"):
            if not self.allowed(mutate=True):
                return
            if re.fullmatch(r"/api/streams/[a-f0-9]{32}-\d+\.mp4", path):
                return self.stream_media(path.rsplit("/", 1)[-1])
            if path == "/api/status":
                return self.respond(200, self.app.status())
            if re.fullmatch(r"/api/jobs/[a-f0-9]{32}", path):
                try:
                    return self.respond(200, self.app.job(path.rsplit("/", 1)[-1]))
                except KeyError:
                    pass
        self.respond(404, {"error": "Not found."})

    def stream_media(self, filename):
        key = filename.split("-", 1)[0]
        with self.app.lock:
            job = self.app.jobs.get(key)
            if job is None or not any(c.get("stream") == "/api/streams/"+filename for c in job["chunks"]):
                return self.respond(404, {"error": "Reply not found."})
        file = self.app.directory / filename
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.connection.settimeout(10)
        offset = 0
        deadline = time.monotonic() + 90
        try:
            while time.monotonic() < deadline:
                with self.app.lock:
                    current = self.app.jobs.get(key)
                    if not current or current["cancel"].is_set() or current["state"] in {"failed", "cancelled"}:
                        return
                    done = current["state"] == "done"
                if file.exists():
                    # Open only during each read so Windows can remove cancelled files.
                    with file.open("rb") as source:
                        source.seek(offset)
                        data = source.read(65536)
                    if data:
                        self.wfile.write(data)
                        self.wfile.flush()
                        offset += len(data)
                        continue
                if done:
                    return
                time.sleep(.025)
        except (OSError, TimeoutError):
            return

    def do_POST(self):
        if not self.allowed(mutate=True):
            return
        path = urlparse(self.path).path
        audio = path == "/api/audio"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= (6_000_000 if audio else 16_384):
                return self.respond(413, {"error": "Request too large or empty."})
            if self.headers.get("Transfer-Encoding"):
                return self.respond(400, {"error": "Content-Length required."})
            self.connection.settimeout(10)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request.")
            if audio:
                if self.headers.get("Content-Type", "").split(";")[0] != "audio/wav":
                    raise ValueError("Use WAV audio.")
                key = self.app.submit("", self.headers.get("X-Reply-Mode", "voice"), self.headers.get("X-Scene", "mira"), raw)
                return self.respond(202, {"id": key})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("Use JSON.")
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError("Use a JSON object.")
            if path == "/api/turn":
                key = self.app.submit(body.get("text"), body.get("mode", "voice"), body.get("scene", "mira"))
                return self.respond(202, {"id": key})
            if path == "/api/cancel":
                self.app.cancel(body.get("id"))
                return self.respond(200, {"ok": True})
            if path == "/api/memory":
                self.app.store.remember(body.get("memory"))
                return self.respond(200, {"ok": True})
            if path == "/api/facts/delete":
                self.app.store.forget(body.get("key"))
                return self.respond(200, {"ok": True})
            if path == "/api/reset":
                self.app.reset()
                return self.respond(200, {"ok": True})
            return self.respond(404, {"error": "Not found."})
        except BlockingIOError as error:
            self.respond(409, {"error": str(error)})
        except RuntimeError as error:
            self.respond(503, {"error": str(error)})
        except (ValueError, TypeError, TimeoutError) as error:
            self.respond(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    app = Application()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server.app = app
    threading.Thread(target=app.warm, daemon=True).start()
    print(f"AI-mate local: http://127.0.0.1:{args.port} (single user, non-explicit prototype)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        app.cancel()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
