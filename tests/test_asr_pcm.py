"""Exercise the untrusted recording boundary without loading inference weights."""
import io
import math
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import Mock

from local_app.models import Models

try:
    import numpy as np
    import scipy.signal
except ImportError:
    np = None


@unittest.skipIf(np is None, 'Local audio runtime is not installed.')
class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.model = Models.__new__(Models)
        self.model.asr = Mock()
        self.model.asr.transcribe.return_value = ([SimpleNamespace(text=' Hello. ')], None)

    def recording(self, rate=16000, duration=.2, channels=1, width=2, pcm=None):
        if pcm is None:
            count = round(rate * duration)
            samples = (3000 * np.sin(2 * np.pi * 440 * np.arange(count) / rate)).astype('<i2')
            pcm = samples.tobytes() * channels
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(width)
            wav.setframerate(rate)
            wav.writeframes(pcm)
        return stream.getvalue()

    def test_pcm_scaling_and_no_decoder_roundtrip(self):
        samples = np.tile(np.array([-32768, -1, 0, 1, 32767], dtype='<i2'), 640)
        self.assertEqual(self.model.transcribe(self.recording(pcm=samples.tobytes())), 'Hello.')
        audio = self.model.asr.transcribe.call_args.args[0]
        self.assertIsInstance(audio, np.ndarray)
        self.assertEqual(audio.dtype, np.float32)
        np.testing.assert_array_equal(audio, samples.astype(np.float32) / 32768)
        self.assertEqual(self.model.asr.transcribe.call_args.kwargs, {
            'language': 'en', 'beam_size': 1, 'vad_filter': True,
            'condition_on_previous_text': False})

    def test_browser_sample_rates_preserve_duration_and_pitch(self):
        for rate in (8000, 16000, 22050, 24000, 44100, 48000, 96000):
            with self.subTest(rate=rate):
                self.model.transcribe(self.recording(rate=rate))
                audio = self.model.asr.transcribe.call_args.args[0]
                self.assertEqual(len(audio), math.ceil(round(rate * .2) * 16000 / rate))
                self.assertEqual(audio.dtype, np.float32)
                frequencies = np.fft.rfftfreq(len(audio), 1 / 16000)
                self.assertAlmostEqual(frequencies[np.argmax(abs(np.fft.rfft(audio)))], 440, delta=5)

    def test_silence_and_very_quiet_input_skip_inference(self):
        for peak in (0, 99, -99):
            with self.subTest(peak=peak):
                self.assertEqual(self.model.transcribe(self.recording(pcm=np.full(3200, peak, dtype='<i2').tobytes())), '')
        self.model.asr.transcribe.assert_not_called()

    def test_invalid_recordings_never_reach_model(self):
        for raw in (b'invalid', self.recording()[:-2], self.recording(channels=2),
                    self.recording(width=1), self.recording(rate=7999),
                    self.recording(rate=96001), self.recording(duration=.1),
                    self.recording(duration=30.01), self.recording(pcm=b'')):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                self.model.transcribe(raw)
        self.model.asr.transcribe.assert_not_called()

    def test_duration_boundaries_are_accepted(self):
        for duration in (.15, 30):
            with self.subTest(duration=duration):
                self.assertEqual(self.model.transcribe(self.recording(duration=duration)), 'Hello.')


if __name__ == '__main__':
    unittest.main()
