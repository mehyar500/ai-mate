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
        try:
            yield sink
        except BaseException:
            event.set()
            raise
        finally:
            row['producer_done'] = True

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
            except queue.Empty:
                if clip['producer_done']:
                    clip['finished'] = True
                    clip['completed_s'] = time.perf_counter()-clip['started']
                elif clip['start_s'] is not None:
                    clip['underflows'] += 1
                    clip['audio_pause_until'] = seconds + 1/20
                    picture = self.last
        if picture is None:
            picture = self.session.idle[int(seconds*24) % len(self.session.idle)]
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


