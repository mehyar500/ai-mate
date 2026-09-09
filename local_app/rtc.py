"""Shared audio/video playback queues for optional WebRTC transport.

Requires the optional aiortc environment. Signaling and benchmark fixture
selection belong to callers; importing this module starts no server.
"""
from contextlib import contextmanager
import asyncio
from fractions import Fraction
import hashlib
import math
import queue
import threading
import time

import av
from aiortc import AudioStreamTrack, VideoStreamTrack
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


class PlaybackSession:
    def __init__(self, renderer, idle, fixtures, folder, transport='webrtc', *, benchmark=False):
        self.renderer, self.idle, self.fixtures, self.folder = renderer, idle, fixtures, folder
        self.benchmark = benchmark
        self.sequence = 0
        self.last_sent_position = None
        self.idle_frame = None
        self.clock_start = None
        self.clip = None
        self.rows = []
        self.cancel = threading.Event()
        self.transport = transport
        self.lock = threading.Lock()
        self.receiver_ready = transport == 'mse'

    async def pace(self, seconds):
        loop = asyncio.get_running_loop()
        if self.clock_start is None:
            self.clock_start = loop.time()
        await asyncio.sleep(max(0, self.clock_start + seconds - loop.time()))

    def prepare_output(self, index, fixture, event=None):
        rate, pcm = wavfile.read(fixture['wav'])
        if pcm.dtype != np.int16 or pcm.ndim != 1 or not 0 < len(pcm)/rate < 10:
            raise ValueError('Invalid synthetic WAV.')
        common = math.gcd(rate, 48000)
        pcm = np.clip(np.rint(resample_poly(pcm.astype(float), 48000//common, rate//common)), -32768, 32767).astype(np.int16)
        self.sequence += 1
        # Old diagnostics must not retain PCM and queued image buffers forever.
        if not self.benchmark:
            self.rows[:] = self.rows[-7:]
        row = {'index': self.sequence, 'case': fixture['case'], 'started': time.perf_counter(),
               'queue': queue.Queue(maxsize=32), 'pcm': pcm, 'start_s': None, 'producer_done': False,
               'finished': False, 'underflows': 0, 'frame_count': 0, 'first_frame_ready_s': None,
               'max_queue': 0, 'event': event, 'fixture_index': index, 'audio_sha256': hashlib.sha256(fixture['wav'].read_bytes()).hexdigest()}
        self.rows.append(row)
        self.clip = row

        def sink(frame, frame_index, fps):
            if fps != 20 or frame_index != row['frame_count']:
                raise ValueError('Frame order/rate changed.')
            if row['first_frame_ready_s'] is None:
                row['first_frame_ready_s'] = time.perf_counter()-row['started']
            if self.transport == 'mse':
                row['frame_count'] += 1
                return
            # Synthetic timing marker only; the archive written by the renderer
            # remains unmarked. A copy prevents mutations of cached body media.
            frame = frame.copy()
            if self.benchmark:
                frame[-16:, :16] = (0, 255, row['index']*9)
            while True:
                if event is not None:
                    from local_app.models import check_cancel
                    check_cancel(event)
                if self.cancel.is_set():
                    raise RuntimeError('Benchmark stopped.')
                try:
                    row['queue'].put((frame_index, frame), timeout=.1)
                    break
                except queue.Full:
                    continue
            row['frame_count'] += 1
            row['max_queue'] = max(row['max_queue'], row['queue'].qsize())

        return row, sink

    @contextmanager
    def output(self, key, index, audio_path, event):
        """Attach the central engine to this isolated RTC queue."""
        from local_app.models import check_cancel
        deadline = time.monotonic()+15
        while self.clip and not self.clip['finished'] and not (self.clip.get('event') and self.clip['event'].is_set()):
            check_cancel(event)
            if self.cancel.is_set() or time.monotonic() >= deadline:
                raise RuntimeError('RTC playback did not drain.')
            time.sleep(.02)
        check_cancel(event)
        with self.lock:
            if not self.receiver_ready or self.cancel.is_set() or (self.benchmark and self.sequence >= 24):
                raise RuntimeError('RTC receiver unavailable or experiment limit reached.')
            row, sink = self.prepare_output(index, {'case': 'engine', 'wav': audio_path}, event)
            row['worker'] = threading.current_thread()
            row['job_id'] = key
            row['chunk_index'] = index
        try:
            yield sink
        except BaseException:
            event.set()
            raise
        finally:
            row['producer_done'] = True

    def playback_position(self):
        """Last frame handed to RTP, not a browser presentation acknowledgement."""
        position = self.last_sent_position
        return {'id': position[0], 'playback': {'index': position[1], 'time_s': position[2]/20}} if position else None

    def safe_rows(self):
        omit = {'queue', 'pcm', 'worker', 'started', 'event'}
        return [{k: v for k, v in row.copy().items() if k not in omit} for row in self.rows.copy()]


class Picture(VideoStreamTrack):
    def __init__(self, session):
        super().__init__()
        self.session, self.tick, self.last = session, 0, None

    async def recv(self):
        seconds = self.tick/20
        await self.session.pace(seconds)
        clip = self.session.clip
        stopped = self.session.cancel.is_set() or bool(clip and clip.get('event') and clip['event'].is_set())
        picture = (self.last if self.last is not None else self.session.idle[0]) if stopped else None
        if not stopped and clip and not clip['finished']:
            try:
                index, picture = clip['queue'].get_nowait()
                if clip['start_s'] is None:
                    clip['start_s'] = seconds
                    clip['first_frame_sent_s'] = time.perf_counter()-clip['started']
                self.last = picture
                if clip.get('job_id') is not None:
                    self.session.last_sent_position = (clip['job_id'], clip['chunk_index'], index)
            except queue.Empty:
                if clip['producer_done']:
                    clip['finished'] = True
                    clip['completed_s'] = time.perf_counter()-clip['started']
                elif clip['start_s'] is not None:
                    clip['underflows'] += 1
                    clip['audio_pause_until'] = seconds + 1/20
                    picture = self.last
        if picture is None:
            select_idle = getattr(self.session, 'idle_frame', None)
            picture = select_idle(seconds, self.last) if select_idle else self.session.idle[int(seconds*24) % len(self.session.idle)]
        self.last = picture
        frame = av.VideoFrame.from_ndarray(picture, format='bgr24')
        frame.pts, frame.time_base = self.tick*4500, Fraction(1, 90000)
        self.tick += 1
        return frame


class Speech(AudioStreamTrack):
    def __init__(self, session):
        super().__init__()
        self.session, self.tick = session, 0

    async def recv(self):
        seconds = self.tick*.02
        await self.session.pace(seconds)
        pcm = np.zeros((1, 960), dtype=np.int16)
        clip = self.session.clip
        if not self.session.cancel.is_set() and clip and not (clip.get('event') and clip['event'].is_set()) and clip['start_s'] is not None:
            offset = round((seconds-clip['start_s']-clip.get('underflows', 0)/20)*48000)
            pause_samples = max(0, min(960, round((clip.get('audio_pause_until', 0)-seconds)*48000)))
            begin, end = max(0, offset+pause_samples), min(len(clip['pcm']), offset+960)
            if begin < end:
                pcm[0, begin-offset:end-offset] = clip['pcm'][begin:end]
        frame = av.AudioFrame.from_ndarray(pcm, format='s16', layout='mono')
        frame.pts, frame.sample_rate, frame.time_base = self.tick*960, 48000, Fraction(1, 48000)
        self.tick += 1
        return frame




class LocalCall:
    """Single-user, same-PC RTC connection for the optional local call UI."""
    def __init__(self, engine):
        self.engine, self.session, self.peer = engine, None, None
        self.gate = asyncio.Lock()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def request(self, action, payload):
        future = asyncio.run_coroutine_threadsafe(self.dispatch(action, payload), self.loop)
        try:
            return future.result(timeout=12)
        except TimeoutError:
            future.cancel()
            raise RuntimeError('Call connection timed out.')

    async def dispatch(self, action, payload):
        async with self.gate:
            return await self._dispatch(action, payload)

    async def _dispatch(self, action, payload):
        if action == 'close':
            await self.close()
            return {'ok': True}
        if action == 'stop':
            session = self.session
            if session is None:
                return {'ok': True, 'pose_preserved': False}
            clip = session.clip
            position = session.playback_position()
            # Never preserve a previous reply's frame while a new reply is pending.
            if (position and clip and not clip['finished']
                    and position['id'] == clip.get('job_id')
                    and position['playback']['index'] == clip.get('chunk_index')):
                result = await asyncio.to_thread(self.engine.cancel, position['id'], position['playback'])
                return {**result, 'position_basis': 'last_sent_frame'}
            self.engine.cancel()
            return {'ok': True, 'pose_preserved': False}
        if action == 'state':
            clip = self.session.clip if self.session else None
            return {'connection_state': self.peer.connectionState if self.peer else 'closed',
                    'connected': bool(self.peer and self.peer.connectionState == 'connected'),
                    'playing': bool(clip and not clip['finished'] and not (clip.get('event') and clip['event'].is_set())),
                    'started': bool(clip and clip['start_s'] is not None)}
        if action != 'offer':
            raise ValueError('Unknown call action.')
        if self.peer or self.engine.busy or not self.engine.ready:
            raise BlockingIOError('Call unavailable or already connected.')
        from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription, RTCRtpSender
        from aioice.mdns import create_mdns_protocol
        from scripts.webrtc_signaling import resolve_local_offer
        import ifaddr
        addresses = {'127.0.0.1', '::1'} | {ip.ip if isinstance(ip.ip, str) else ip.ip[0]
            for adapter in ifaddr.get_adapters() for ip in adapter.ips}
        protocol = await create_mdns_protocol()
        try:
            payload = await resolve_local_offer(payload, addresses, protocol.resolve)
        finally:
            await protocol.close()
        # Reserve the peer before awaiting setup; a second offer cannot replace it.
        peer = self.peer = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        try:
            idle, near = await asyncio.to_thread(self.load_idle)
            session = self.session = PlaybackSession(None, idle, [], self.engine.directory)
            def select_idle(seconds, last):
                with self.engine.lock:
                    held, busy, pose = self.engine.hold_still, self.engine.busy, self.engine.performance_state
                if last is not None and (held or busy or pose not in {'base', 'near'}):
                    return last
                frames = near if pose == 'near' else idle
                return frames[int(seconds*24) % len(frames)] if frames else (last if last is not None else idle[0])
            session.idle_frame = select_idle
            self.engine.frame_output = session.output
            @peer.on('connectionstatechange')
            async def changed():
                session.receiver_ready = peer.connectionState == 'connected'
                if peer.connectionState in {'failed', 'closed'} and self.peer is peer:
                    await self.close()
            peer.addTrack(Picture(session)); peer.addTrack(Speech(session))
            for transceiver in peer.getTransceivers():
                if transceiver.kind == 'video':
                    transceiver.setCodecPreferences([c for c in RTCRtpSender.getCapabilities('video').codecs if c.mimeType == 'video/H264'])
            await peer.setRemoteDescription(RTCSessionDescription(**payload))
            await peer.setLocalDescription(await peer.createAnswer())
            return {'type':peer.localDescription.type, 'sdp':peer.localDescription.sdp}
        except BaseException:
            await self.close()
            raise

    def load_idle(self):
        import cv2
        def read(path):
            frames = []
            if path:
                capture = cv2.VideoCapture(str(path))
                try:
                    while len(frames) < 144:
                        ok, frame = capture.read()
                        if not ok:
                            break
                        frames.append(frame)
                finally:
                    capture.release()
            return frames
        idle, near = read(self.engine.idle_video), read(self.engine.near_idle_video)
        if not idle:
            raise RuntimeError('Reviewed call video is unavailable.')
        return idle, near

    async def close(self):
        peer, session = self.peer, self.session
        self.peer = self.session = None
        if session:
            session.cancel.set()
            if self.engine.frame_output == session.output:
                self.engine.cancel()
                self.engine.frame_output = None
        if peer:
            await peer.close()

    def shutdown(self):
        self.request('close', {})
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=3)
        if not self.thread.is_alive():
            self.loop.close()
