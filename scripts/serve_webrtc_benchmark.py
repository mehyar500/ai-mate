"""Bounded local WebRTC experiment using real GPU frames and retained synthetic WAVs.

No private memory, hosted inference, physical capture or public signaling.
Signaling is same-origin/token protected on 127.0.0.1:8766. ICE has no external
STUN/TURN servers. This is an isolated transport benchmark, not the live app.
"""
import argparse
import hashlib
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.cache/webrtc-deps'), str(ROOT)]

import av
from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription, RTCRtpSender
import cv2
import ifaddr

from local_app.media import load_reviewed_idle
from local_app.visual import PortraitRenderer
from scripts.review_lip_sync import preview_idle
from scripts.webrtc_signaling import resolve_local_offer


from local_app.rtc import PlaybackSession, Picture, Speech


class Session(PlaybackSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, benchmark=True)

    def begin(self, index):
        with self.lock:
            return self._begin(index)

    def _begin(self, index):
        if not self.receiver_ready:
            raise BlockingIOError('Connect the benchmark receiver first.')
        if self.clip and not self.clip['finished']:
            raise BlockingIOError('Wait for the current synthetic reply.')
        if len(self.rows) >= 24 or type(index) is not int or not 0 <= index < len(self.fixtures):
            raise ValueError('Select a bounded synthetic fixture.')
        preview_idle()
        fixture = self.fixtures[index]
        row, sink = self.prepare_output(index, fixture)

        def render():
            try:
                row['render'] = self.renderer.render(fixture['wav'], self.folder/f"reply-{row['index']:02}.mp4", self.cancel,
                    'fullbody', streaming=True, motion_path=fixture['source'], loop_motion=True, reuse_motion=True, frame_sink=sink)
            except Exception as error:
                row['error'] = type(error).__name__ + ': ' + str(error)[:300]
            finally:
                row['producer_done'] = True
                if self.transport == 'mse':
                    row['finished'] = True
        row['worker'] = threading.Thread(target=render, daemon=True)
        row['worker'].start()
        return {'index': row['index'], 'case': row['case'], 'duration_s': len(row['pcm'])/48000}



PAGE = b'''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Mate WebRTC transport experiment</title><style>body{margin:0;background:#111;color:white;font:16px system-ui}video{height:85dvh;max-width:100%;display:block;margin:auto}button{font:inherit;min-height:44px}p{margin:12px}</style>
<video id="video" playsinline autoplay></video><p>Isolated transport test. Synthetic speech, prepared body, newly generated lips. No microphone.</p><button id="connect">Connect test call</button><p id="status"></p><script type="module" src="/client.js"></script></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def allowed(self, mutate=False):
        origin = 'http://127.0.0.1:8766'
        if (self.headers.get('Host') != '127.0.0.1:8766' or self.headers.get('Origin') not in (None, origin)
                or self.headers.get('Sec-Fetch-Site') == 'cross-site'
                or (mutate and not secrets.compare_digest(self.headers.get('X-Local-Token', ''), self.server.token))):
            self.respond(403, {'error': 'Local benchmark origin and token required.'})
            return False
        return True

    def respond(self, code, payload, mime='application/json'):
        data = json.dumps(payload).encode() if mime == 'application/json' else payload
        self.send_response(code)
        for key, value in [('Content-Type', mime), ('Content-Length', str(len(data))), ('Cache-Control', 'no-store'),
                           ('X-Content-Type-Options', 'nosniff'), ('Cross-Origin-Resource-Policy', 'same-origin'),
                           ('Permissions-Policy', 'camera=(), microphone=()'),
                           ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")]:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.allowed():
            return
        if self.path == '/':
            return self.respond(200, PAGE, 'text/html')
        if self.path == '/client.js':
            name = 'mse_benchmark_client.js' if self.server.session.transport == 'mse' else 'webrtc_benchmark_client.js'
            return self.respond(200, (ROOT/'scripts'/name).read_bytes(), 'text/javascript')
        if self.path == '/media-sync.mjs':
            return self.respond(200, (ROOT/'local_app/web/media-sync.mjs').read_bytes(), 'text/javascript')
        if self.path == '/bootstrap':
            return self.respond(200, {'token': self.server.token, 'fixtures': len(self.server.session.fixtures), 'transport': self.server.session.transport, 'jitter_ms': self.server.jitter_ms})
        match = re.fullmatch(r'/(audio|stream)/(\d{1,2})', self.path)
        if match and self.server.session.transport == 'mse':
            index = int(match[2])-1
            if not 0 <= index < len(self.server.session.rows):
                return self.respond(404, {'error': 'Unknown synthetic reply.'})
            row = self.server.session.rows[index]
            if match[1] == 'audio':
                return self.respond(200, self.server.session.fixtures[row['fixture_index']]['wav'].read_bytes(), 'audio/wav')
            if not self.allowed(mutate=True):
                return
            path = self.server.session.folder/f"reply-{index+1:02}.mp4"
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.close_connection = True
            self.connection.settimeout(10)
            offset, deadline = 0, time.monotonic()+90
            try:
                while time.monotonic() < deadline and not self.server.session.cancel.is_set():
                    if path.exists():
                        with path.open('rb') as source:
                            source.seek(offset)
                            data = source.read(65536)
                        if data:
                            self.wfile.write(data)
                            self.wfile.flush()
                            offset += len(data)
                            continue
                    if row['producer_done']:
                        return
                    time.sleep(.025)
            except OSError:
                # Receiver cancellation is normal; never send another response
                # after the streaming headers have already been written.
                return
            return
        return self.respond(404, {'error': 'Unknown route.'})

    def do_POST(self):
        if not self.allowed(mutate=True):
            return
        try:
            if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                raise ValueError('Use bounded JSON.')
            length = int(self.headers.get('Content-Length', 0))
            if not 1 <= length <= 32_000:
                raise ValueError('Request exceeds the benchmark limit.')
            self.connection.settimeout(10)
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Use a JSON object.')
            if self.path == '/offer':
                if self.server.session.transport != 'webrtc':
                    raise ValueError('This run uses MSE.')
                future = asyncio.run_coroutine_threadsafe(self.server.offer(payload), self.server.loop)
                try:
                    return self.respond(200, future.result(timeout=15))
                except TimeoutError:
                    future.cancel()
                    raise
            if self.path == '/run':
                return self.respond(200, self.server.session.begin(payload.get('fixture')))
            if self.path == '/results':
                return self.respond(200, {'rows': self.server.session.safe_rows()})
            if self.path == '/done':
                self.server.finished.set()
                return self.respond(200, {'stopping': True})
            return self.respond(404, {'error': 'Unknown route.'})
        except BlockingIOError as error:
            self.respond(409, {'error': str(error)})
        except (ValueError, TypeError):
            self.respond(400, {'error': 'Invalid benchmark request.'})
        except Exception as error:
            self.respond(503, {'error': type(error).__name__})


async def main(args):
    folder = ROOT/'generated/local-app/audit'/('webrtc-'+args.label)
    folder.mkdir(exist_ok=False)
    source = ROOT/'generated/local-app/audit/voice-video-qualification-lip-crop-selected'
    qualification = json.loads((source/'qualification.json').read_text())
    fixtures = []
    for row in qualification['results']:
        if row['case'] not in {'description', 'unsupported', 'conversation'}:
            continue
        job = row['job']
        fixtures.append({'case': row['case'], 'wav': source/'retained-media'/(job['id']+'-0.wav'),
                         'source': load_reviewed_idle(source, job['prepared_pose'])})
    if len(fixtures) != 3 or not all(f['source'] for f in fixtures):
        raise ValueError('Three reviewed synthetic fixtures are required.')
    preview_idle()
    renderer = PortraitRenderer(decoder_backend='tensorrt')
    renderer.prime_motion(list({f['source'] for f in fixtures}), threading.Event())
    capture = cv2.VideoCapture(str(load_reviewed_idle(source, 'base')))
    idle = []
    while len(idle) < 144:
        ok, frame = capture.read()
        if not ok:
            break
        idle.append(frame)
    capture.release()
    if not idle:
        raise ValueError('No reviewed idle frames.')
    session = Session(renderer, idle, fixtures, folder, args.transport)
    peers = []

    async def offer(payload):
        if peers:
            raise BlockingIOError('One benchmark connection at a time.')
        from aioice.mdns import create_mdns_protocol
        protocol = None
        resolver_lock = asyncio.Lock()
        async def resolve(name):
            nonlocal protocol
            async with resolver_lock:
                if protocol is None:
                    protocol = await create_mdns_protocol()
            return await protocol.resolve(name)
        try:
            payload = await resolve_local_offer(payload, server.local_addresses, resolve)
        finally:
            if protocol is not None:
                await protocol.close()
        peer = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        peers.append(peer)
        @peer.on('connectionstatechange')
        async def state_changed():
            if peer not in peers:
                return
            session.receiver_ready = peer.connectionState == 'connected'
            if peer.connectionState in {'closed', 'failed'}:
                session.cancel.set()
                server.finished.set()
        try:
            # aiortc intersects preferences while applying the remote offer.
            # Setting these afterwards leaves VP8 negotiated despite the intent.
            peer.addTrack(Picture(session))
            peer.addTrack(Speech(session))
            for transceiver in peer.getTransceivers():
                if transceiver.kind == 'video':
                    transceiver.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs if c.mimeType=='video/H264'])
            await peer.setRemoteDescription(RTCSessionDescription(**payload))
            await peer.setLocalDescription(await peer.createAnswer())
            return {'type': peer.localDescription.type, 'sdp': peer.localDescription.sdp}
        except BaseException:
            peers.remove(peer)
            await peer.close()
            raise

    server = ThreadingHTTPServer(('127.0.0.1', 8766), Handler)
    server.daemon_threads = True
    server.token, server.session, server.loop, server.offer = secrets.token_urlsafe(32), session, asyncio.get_running_loop(), offer
    server.local_addresses = {'127.0.0.1', '::1'} | {ip.ip if isinstance(ip.ip, str) else ip.ip[0] for adapter in ifaddr.get_adapters() for ip in adapter.ips}
    server.jitter_ms = args.jitter_ms
    server.finished = threading.Event()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(json.dumps({'ready': True, 'port': 8766, 'fixtures': len(fixtures), 'transport': args.transport}), flush=True)
    try:
        deadline = time.monotonic()+360
        while not server.finished.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(.2)
    finally:
        session.cancel.set()
        for peer in peers:
            await peer.close()
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        for row in session.rows:
            await asyncio.to_thread(row['worker'].join, 10)
        (folder/'server-results.json').write_text(json.dumps({'rows': session.safe_rows(),
            'scope': 'Synthetic local GPU-to-browser transport benchmark. No ASR, dialogue or TTS time; WAVs are retained fixed inputs. No external ICE servers. Marked copies go to RTC only; archived renders are unmarked.',
            'aiortc': '1.15.0', 'av': av.__version__, 'face_shift': renderer.face_shift,
            'transport': args.transport,
            'jitter_ms': args.jitter_ms,
            'source_video_sha256': {f['case']: hashlib.sha256(f['source'].read_bytes()).hexdigest() for f in fixtures}}, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--transport', choices=['webrtc', 'mse'], default='webrtc')
    parser.add_argument('--jitter-ms', type=int, choices=[0, 20, 50])
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        parser.error('Use a short lowercase label.')
    asyncio.run(main(args))
