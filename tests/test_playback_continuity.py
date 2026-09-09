"""Interruption must retain the displayed pose without accepting client media paths."""
import importlib.util
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from local_app.engine import CompanionEngine
from local_app.playback import capture_playback_frame, stopped_pose, validate_playback
from local_app.visual import motion_duration


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = CompanionEngine(self.root)
        self.app.ready = True
        self.key = 'a' * 32
        self.app.generation = 1
        self.source = self.root / (self.key + '-0.mp4')
        self.source.write_bytes(b'synthetic video')
        self.app.jobs[self.key] = {'id': self.key, 'state': 'done', 'cancel': threading.Event(),
            'chunks': [], 'metrics': {}, '_generation': 1, '_playback': {0: {
                'scene': 'fullbody', 'pose': None, 'cursor': .4, 'transition': None, 'start_s': 0, 'fps': 20}}}

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def capture(source, destination, seconds):
        destination.write_bytes(source.read_bytes() + b' displayed frame')
        return {'time_s': seconds, 'frame': int(seconds * 20)}

    def stop(self, seconds=.6):
        return self.app.cancel(self.key, {'index': 0, 'time_s': seconds})

    def test_strict_descriptor_rejects_paths_invalid_numbers_and_types(self):
        for value in (None, [], {}, {'index': 0, 'time_s': 1, 'path': '../secret'},
                      {'index': True, 'time_s': 0}, {'index': -1, 'time_s': 0},
                      *({'index': 0, 'time_s': n} for n in [-1, 31, float('nan'), float('inf'), True, '1'])):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_playback(value)
        with self.assertRaises(ValueError):
            self.app.cancel('../private', {'index': 0, 'time_s': 0})
        with self.assertRaises(ValueError):
            self.app.cancel(self.key, {'index': 1, 'time_s': 0})
        self.assertFalse(self.app.jobs[self.key]['cancel'].is_set())

    def test_stale_reply_cannot_roll_back_new_generation(self):
        self.app.generation += 1
        with self.assertRaises(BlockingIOError):
            self.stop()
        self.assertIsNone(self.app.pose)

    def test_completed_video_stop_replaces_generated_endpoint_and_is_idempotent(self):
        previous = self.root/'old.png'; previous.write_bytes(b'generated endpoint')
        self.app.pose = ('fullbody', previous)
        self.app.performance_state = 'near'
        with patch('local_app.playback.capture_playback_frame', side_effect=self.capture) as capture:
            result = self.stop()
            self.assertEqual(self.stop(.9), result)
        self.assertEqual(capture.call_count, 1)
        self.assertTrue(result['pose_preserved'])
        self.assertEqual(self.app.visual_cursor, .4)
        self.assertIsNone(self.app.performance_state)
        self.assertIsNone(result['idle_video'])
        self.assertFalse(previous.exists())
        self.assertIn(b'displayed frame', self.app.pose[1].read_bytes())
        self.assertEqual(list(self.root.glob('playback-*.mp4')), [])
        self.assertFalse(any(k.startswith('_') for k in self.app.job(self.key)))

    def test_worker_cleanup_cannot_remove_snapshot_and_submission_waits_for_capture(self):
        def capture(source, destination, seconds):
            self.assertTrue(self.app.jobs[self.key]['cancel'].is_set())
            self.app.remove_media(self.key)
            self.assertTrue(self.app.status()['busy'])
            with self.assertRaises(BlockingIOError):
                self.app.submit('Next reply', 'text', 'mira')
            with self.assertRaises(BlockingIOError):
                self.stop()
            return self.capture(source, destination, seconds)
        with patch('local_app.playback.capture_playback_frame', side_effect=capture):
            self.assertTrue(self.stop()['pose_preserved'])
        self.assertFalse(self.app.status()['busy'])
        self.assertTrue(self.app.pose[1].exists())

    def test_reset_during_capture_cannot_restore_deleted_state(self):
        self.app.store.remember('Synthetic memory')
        def capture(source, destination, seconds):
            self.app.reset()
            return self.capture(source, destination, seconds)
        with patch('local_app.playback.capture_playback_frame', side_effect=capture):
            result = self.stop()
        self.assertTrue(result['superseded'])
        self.assertIsNone(self.app.pose)
        self.assertIsNone(self.app.visual_cursor)
        self.assertEqual(self.app.scene, 'mira')
        self.assertEqual(self.app.store.snapshot(), {'memory': '', 'turns': []})
        self.assertEqual(list(self.root.glob('playback-*')), [])

    def test_capture_failure_still_cancels_and_cleans_temporary_files(self):
        def fail(source, destination, seconds):
            destination.write_bytes(b'partial')
            raise ValueError('Synthetic truncated media')
        with patch('local_app.playback.capture_playback_frame', side_effect=fail):
            result = self.stop()
        self.assertFalse(result['pose_preserved'])
        self.assertTrue(self.app.jobs[self.key]['cancel'].is_set())
        self.assertFalse(self.app.playback_pending)
        self.assertEqual(list(self.root.glob('playback-*')), [])

    def test_missing_video_still_stops_worker(self):
        self.source.unlink()
        self.assertFalse(self.stop()['pose_preserved'])
        self.assertTrue(self.app.jobs[self.key]['cancel'].is_set())
        self.assertFalse(self.app.playback_pending)

    def test_reverse_and_continuation_use_remaining_source_duration(self):
        with patch('local_app.playback.video_duration', return_value=3):
            for destination, expected in [('near', .4), ('base', .6)]:
                metadata = {'transition': {'path': self.source, 'to': destination}, 'start_s': .6}
                pose, progress = stopped_pose(metadata, .6)
                self.assertIsNone(pose)
                self.assertAlmostEqual(progress, expected)
        self.assertEqual(motion_duration(.5, 72, 24, start_s=2), 1)
        self.assertEqual(motion_duration(2, 72, 24, start_s=2), 2)
        for offset in [-1, 4, float('nan')]:
            with self.assertRaises(ValueError):
                motion_duration(1, 72, 24, start_s=offset)

    def test_gesture_interruption_never_becomes_an_approach_cursor(self):
        with patch('local_app.playback.video_duration', return_value=4):
            for pose in ['base','near']:
                metadata = {'transition': {'kind':'gesture','path':self.source,'from':pose,'to':pose},'start_s':0}
                self.assertEqual(stopped_pose(metadata, 0), (None, None))
                self.assertEqual(stopped_pose(metadata, 1.5), (None, None))
                self.assertEqual(stopped_pose(metadata, 4), (pose, None))
                self.assertEqual(stopped_pose(metadata, 5), (pose, None))

    @unittest.skipUnless(importlib.util.find_spec('cv2'), 'Optional local video runtime is not installed')
    def test_real_decoded_timestamp_selects_middle_frame_and_rejects_unavailable_tail(self):
        import cv2
        import numpy as np
        writer = cv2.VideoWriter(str(self.source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 64))
        try:
            for index in range(20):
                writer.write(np.full((64, 64, 3), index * 10, np.uint8))
        finally:
            writer.release()
        target = self.root/'frame.png'
        result = capture_playback_frame(self.source, target, .7)
        self.assertAlmostEqual(result['time_s'], .7)
        self.assertEqual(result['frame'], 7)
        self.assertAlmostEqual(float(cv2.imread(str(target)).mean()), 70, delta=5)
        with self.assertRaises(ValueError):
            capture_playback_frame(self.source, target, 3)
        with patch('cv2.imwrite', side_effect=cv2.error('Synthetic decoder error')):
            with self.assertRaises(ValueError):
                capture_playback_frame(self.source, target, .7)


if __name__ == '__main__':
    unittest.main()
