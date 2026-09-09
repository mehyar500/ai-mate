import unittest

from local_app.visual import audio_left_padding, motion_duration


class VisualTimingTests(unittest.TestCase):
    def test_whisper_context_tracks_actual_video_rate(self):
        self.assertEqual(audio_left_padding(20),6)
        self.assertEqual(audio_left_padding(25),4)
        self.assertEqual(audio_left_padding(50),2)
        for value in [0,-1,61,float('inf'),float('nan')]:
            with self.assertRaises(ValueError):
                audio_left_padding(value)

    def test_short_reply_does_not_wait_for_ambient_loop(self):
        self.assertEqual(motion_duration(1.25,132,24,loop=True),1.25)
        self.assertEqual(motion_duration(1.25,132,24,loop=False),5.5)

    def test_long_reply_remains_complete_for_loop_and_gesture(self):
        for loop in [False,True]:
            self.assertEqual(motion_duration(13.1,132,24,loop=loop),13.1)

    def test_invalid_speech_metadata_and_overlong_gesture_fail(self):
        for speech in [0,-1,31,float('inf'),float('nan')]:
            with self.assertRaises(ValueError):
                motion_duration(speech,132,24,loop=True)
        for count,fps in [(0,24),(1801,24),(132,0),(132,float('nan'))]:
            with self.assertRaises(RuntimeError):
                motion_duration(1.25,count,fps,loop=True)
        with self.assertRaises(ValueError):
            motion_duration(1.25,1800,24,loop=False)
