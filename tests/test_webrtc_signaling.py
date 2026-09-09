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
    async def test_cancel_silences_buffered_audio_and_holds_last_frame(self):
        try:
            from scripts.serve_webrtc_benchmark import Picture, Speech, np
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
