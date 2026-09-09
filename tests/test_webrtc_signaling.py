import unittest
import io
import tempfile
import threading
import queue
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.webrtc_signaling import validate_offer


class CloudRTCTransportTests(unittest.TestCase):
    def test_fixture_rejects_non_audit_files_and_missing_audio(self):
        from experiments.benchmark_cloud_realtime import fixture_path
        with tempfile.TemporaryDirectory() as folder, patch('experiments.benchmark_cloud_realtime.ROOT', Path(folder)):
            outside = Path(folder)/'private.mp4'
            outside.write_bytes(b'video')
            with self.assertRaises(ValueError):
                fixture_path(outside)
            audit = Path(folder)/'generated/local-app/audit'
            audit.mkdir(parents=True)
            clip = audit/'synthetic.mp4'
            clip.write_bytes(b'video')
            with self.assertRaises(FileNotFoundError):
                fixture_path(clip)
            clip.with_suffix('.wav').write_bytes(b'audio')
            self.assertEqual(fixture_path(clip), clip.resolve())

    def test_client_identifier_and_no_redirect_handler(self):
        from experiments.benchmark_cloud_realtime import exchange, NoRedirect
        opener = MagicMock()
        opener.open.return_value = io.BytesIO(b'{"sessionId":"test"}')
        with patch('urllib.request.build_opener', return_value=opener) as build:
            self.assertEqual(exchange('https://rtc.live.cloudflare.com/v1/apps/test/sessions/new',
                                     {'Authorization': 'Bearer private'})['sessionId'], 'test')
        self.assertIs(build.call_args.args[0], NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), 'AI-Mate-Transport-Probe/1.0')
        self.assertIsNone(request.data)

    def test_foreign_host_never_receives_credentials(self):
        from experiments.benchmark_cloud_realtime import exchange
        with patch('urllib.request.build_opener') as build:
            for url in ['http://rtc.live.cloudflare.com/', 'https://example.com/',
                        'https://rtc.live.cloudflare.com@example.com/']:
                with self.assertRaises(ValueError):
                    exchange(url, {'Authorization': 'Bearer private'})
            build.assert_not_called()

    def test_provider_failure_and_oversized_response_cannot_pass(self):
        from experiments.benchmark_cloud_realtime import exchange
        for raw in [b'{"errorCode":"failed"}', b'{"tracks":[{"errorCode":"failed"}]}',
                    b'{"tracks":null}', b'[]', b'x' * 100001]:
            opener = MagicMock()
            opener.open.return_value = io.BytesIO(raw)
            with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ValueError):
                exchange('https://rtc.live.cloudflare.com/v1/apps/test/sessions/new', {})


def offer(address='127.0.0.1', direction='recvonly'):
    candidate=f'a=candidate:1 1 udp 100 {address} 50000 typ host\r\n'
    return {'type':'offer','sdp':'v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na='+direction+'\r\n'+candidate+
            'm=audio 9 UDP/TLS/RTP/SAVPF 111\r\na='+direction+'\r\n'+candidate}


class RTCPlaybackCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_accepts_long_call_without_marker_or_unbounded_history(self):
        try:
            from scripts.serve_webrtc_benchmark import PlaybackSession
            import numpy as np
            from scipy.io import wavfile
        except ImportError as error:
            self.skipTest(f'Optional RTC test dependencies unavailable: {error.name}')
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder)/'synthetic.wav'
            wavfile.write(audio, 24000, np.zeros(240, dtype=np.int16))
            original = np.full((32,32,3), 77, dtype=np.uint8)
            session = PlaybackSession(None, [original], [], Path(folder))
            session.receiver_ready = True
            for index in range(80):
                with session.output('test', index, audio, threading.Event()) as sink:
                    sink(original, 0, 20)
                _, frame = session.clip['queue'].get_nowait()
                self.assertTrue((frame == original).all())
                session.clip['finished'] = True
            self.assertEqual(session.clip['index'], 80)
            self.assertEqual(len(session.rows), 8)


    async def test_frame_underflow_pauses_audio_clock(self):
        try:
            from scripts.serve_webrtc_benchmark import Picture, Speech
            import numpy as np
        except ImportError as error:
            self.skipTest(f'Optional RTC test dependencies unavailable: {error.name}')
        async def pace(seconds):
            pass
        clip = {'start_s': 0, 'pcm': np.arange(24000, dtype=np.int16),
                'finished': False, 'producer_done': False, 'underflows': 0, 'queue': queue.Queue()}
        session = SimpleNamespace(clip=clip, pace=pace, cancel=threading.Event(),
                                  idle=[np.zeros((32,32,3), dtype=np.uint8)])
        picture, speech = Picture(session), Speech(session)
        picture.last = session.idle[0]
        picture.tick, speech.tick = 2, 5
        await picture.recv()  # no frame at 100ms: hold picture for 50ms
        self.assertFalse((await speech.recv()).to_ndarray().any())
        speech.tick = 7  # audio packet crosses the 150ms pause boundary
        crossing = (await speech.recv()).to_ndarray()[0]
        self.assertFalse(crossing[:480].any())
        self.assertEqual(int(crossing[480]), 4800)
        speech.tick = 8  # 160ms media clock minus the 50ms pause
        self.assertEqual(int((await speech.recv()).to_ndarray()[0,0]), 5280)

    async def test_engine_output_uses_turn_cancellation_without_closing_session(self):
        try:
            from scripts.serve_webrtc_benchmark import Session, Picture, Speech
            import numpy as np
            from scipy.io import wavfile
        except ImportError as error:
            self.skipTest(f'Optional RTC test dependencies unavailable: {error.name}')
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder)/'synthetic.wav'
            wavfile.write(audio, 24000, np.full(24000, 8000, dtype=np.int16))
            session = Session(None, [np.zeros((32,32,3), dtype=np.uint8)], [], Path(folder))
            session.receiver_ready = True
            event = threading.Event()
            with session.output('test', 0, audio, event) as sink:
                original = np.full((32,32,3), 77, dtype=np.uint8)
                sink(original, 0, 20)
                self.assertTrue((original == 77).all())
                picture = Picture(session)
                await picture.recv()
                event.set()
                self.assertFalse((await Speech(session).recv()).to_ndarray().any())
                self.assertFalse(session.cancel.is_set())
            self.assertTrue(session.clip['producer_done'])
            self.assertNotIn('event', session.safe_rows()[0])
            next_event = threading.Event()
            with session.output('next', 0, audio, next_event) as sink:
                sink(original, 0, 20)
            self.assertEqual(len(session.rows), 2)
            self.assertFalse(next_event.is_set())

    async def test_cancel_silences_buffered_audio_and_holds_last_frame(self):
        try:
            from scripts.serve_webrtc_benchmark import Picture, Speech
            import numpy as np
        except ImportError as error:
            self.skipTest(f'Optional RTC test dependencies unavailable: {error.name}')
        async def pace(seconds):
            pass
        clip = {'start_s': 0, 'pcm': np.full(48000, 8000, dtype=np.int16),
                'finished': False, 'queue': queue.Queue()}
        clip['queue'].put((1, np.full((32, 32, 3), 200, dtype=np.uint8)))
        session = SimpleNamespace(clip=clip, pace=pace, cancel=threading.Event(),
                                  idle=[np.zeros((32, 32, 3), dtype=np.uint8)])
        speech, picture = Speech(session), Picture(session)
        picture.last = np.full((32, 32, 3), 77, dtype=np.uint8)
        session.cancel.set()
        self.assertFalse((await speech.recv()).to_ndarray().any())
        self.assertTrue(((await picture.recv()).to_ndarray(format='bgr24') == 77).all())
        self.assertEqual(clip['queue'].qsize(), 1)


class LocalRTCSignalingTests(unittest.TestCase):
    def test_only_this_pc_and_receiving_media_are_accepted(self):
        for address in ['127.0.0.1','192.168.1.5','::1']:
            packet=offer(address)
            self.assertEqual(validate_offer(packet,{address}),packet)
        for address in ['8.8.8.8','192.168.1.6','example.com','random.local']:
            with self.assertRaises(ValueError):
                validate_offer(offer(address),{'127.0.0.1','192.168.1.5'})
        for direction in ['sendrecv','sendonly','inactive']:
            with self.assertRaises(ValueError):
                validate_offer(offer(direction=direction),{'127.0.0.1'})

    def test_shape_relay_capture_and_size_fail_before_creating_peer(self):
        packets=[[],{}, {'type':'answer','sdp':offer()['sdp']},offer()|{'extra':1},
                 {'type':'offer','sdp':'x'*30001}, {'type':'offer','sdp':'v=0\nm=\nm=audio'},
                 {'type':'offer','sdp':offer()['sdp'].replace('typ host','typ relay')},
                 {'type':'offer','sdp':offer()['sdp'].replace('a=recvonly','a=recvonly\r\na=sendrecv')},
                 {'type':'offer','sdp':offer()['sdp']+'m=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n'}]
        for packet in packets:
            with self.subTest(packet=str(packet)[:50]),self.assertRaises(ValueError):
                validate_offer(packet,{'127.0.0.1'})


if __name__=='__main__':unittest.main()


class LocalMDNSTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolved_candidate_is_pinned_and_must_belong_to_pc(self):
        from scripts.webrtc_signaling import resolve_local_offer
        from unittest.mock import AsyncMock
        packet = offer('browser.local')
        resolve = AsyncMock(return_value='127.0.0.1')
        accepted = await resolve_local_offer(packet, {'127.0.0.1'}, resolve)
        self.assertNotIn('browser.local', accepted['sdp'])
        resolve.assert_awaited_once_with('browser.local')
        self.assertIn('browser.local', packet['sdp'])
        for address in ['8.8.8.8', '192.168.1.99', None]:
            with self.assertRaises(ValueError):
                await resolve_local_offer(packet, {'127.0.0.1'}, AsyncMock(return_value=address))

    async def test_malformed_or_capture_offer_never_resolves(self):
        from scripts.webrtc_signaling import resolve_local_offer
        from unittest.mock import AsyncMock
        resolve = AsyncMock()
        for packet in [offer('browser.local', 'sendrecv'), offer('example.com'),
                       offer('browser.local') | {'extra': True}]:
            with self.assertRaises(ValueError):
                await resolve_local_offer(packet, {'127.0.0.1'}, resolve)
        resolve.assert_not_awaited()
