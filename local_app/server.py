"""Loopback HTTP transport. Run with python -m local_app.server."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import secrets
import threading
import time
from urllib.parse import urlparse

from .engine import CompanionEngine, configure_runtime
from .models import ROOT

# Compatibility for existing integration scripts; orchestration has one owner.
Application = CompanionEngine
WEB = ROOT / "local_app/web"


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
        self.send_header("Permissions-Policy", "camera=(), microphone=(self)")
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
                  "/media-sync.mjs": ("media-sync.mjs", "text/javascript"),
                  "/microphone.mjs": ("microphone.mjs", "text/javascript"),
                  "/style.css": ("style.css", "text/css"), "/actions.css": ("actions.css", "text/css"), "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
                  "/icon.svg": ("icon.svg", "image/svg+xml"), "/recorder.js": ("recorder.js", "text/javascript")}
        if path in static:
            file, mime = static[path]
            return self.respond(200, (WEB / file).read_bytes(), mime)
        if path == "/api/bootstrap":
            return self.respond(200, {"token": self.app.token, **self.app.status()})
        if path in {"/portrait/mira.png", "/portrait/garden.png", "/portrait/cafe.png", "/portrait/fullbody.png"}:
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
    configure_runtime()
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
