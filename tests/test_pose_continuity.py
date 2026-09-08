"""State/lifecycle checks; neural image quality is tested separately on the GPU."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

from local_app.server import Application


class FakeVisual:
    def __init__(self):
        self.prepared=[]
        self.count=0
        self.fail=False
        self.after_capture=lambda: None

    def prepare(self, scene, reference_path=None):
        self.prepared.append(reference_path.read_bytes() if reference_path else None)

    def render(self, audio, destination, event, scene, **kwargs):
        if self.fail:
            raise RuntimeError('Synthetic renderer failure')
        self.count+=1
        destination.write_bytes(str(self.count).encode())
        return {}

    def capture_last_frame(self, video, destination):
        destination.write_bytes(video.read_bytes())
        self.after_capture()


class FakeModels:
    def __init__(self):
        self.visual=FakeVisual()

    def plan(self, snapshot, text, mode, scene, available, event):
        return {'reply':'Hello','presentation':'video','scene':scene,'action':text if text in {'wave','closer','farther'} else 'none','facts':[]}

    def load_visual(self):
        return self.visual

    def speech(self, phrase, path):
        path.write_bytes(b'audio')
        return 1


class PoseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=Application(self.temp.name)
        self.app.ready=True
        self.app.models=FakeModels()
        self.visual=self.app.models.visual
        (Path(self.temp.name)/'fullbody.png').write_bytes(b'reference')
        def generate(scene, action, duration, event, destination, reference_path=None):
            destination.write_bytes(b'motion')
            return {}
        self.motion=patch('local_app.motion.generate',side_effect=generate)
        self.generate = self.motion.start()
        def reverse(source, destination, event):
            destination.write_bytes(source.read_bytes()[::-1])
            return {'motion_source':'reversed_previous_approach','fresh_body_generation':False}
        self.reverse_patch = patch('local_app.motion.reverse_approach',side_effect=reverse)
        self.reverse = self.reverse_patch.start()

    def tearDown(self):
        self.motion.stop()
        self.reverse_patch.stop()
        self.temp.cleanup()

    def reply(self,text):
        key=self.app.submit(text,'video','fullbody')
        deadline=time.monotonic()+2
        while self.app.busy and time.monotonic()<deadline:
            time.sleep(.005)
        self.assertFalse(self.app.busy)
        return self.app.job(key)

    def test_ordinary_reply_uses_last_generated_pose_and_removes_previous_file(self):
        self.assertEqual(self.reply('wave')['state'],'done')
        previous=self.app.pose[1]
        self.assertEqual(self.reply('hello')['state'],'done')
        self.assertEqual(self.visual.prepared,[None,b'1'])
        self.assertFalse(previous.exists())
        self.assertEqual(self.app.pose[1].read_bytes(),b'2')

    def test_failed_reply_keeps_previous_pose(self):
        self.reply('wave')
        previous=self.app.pose
        self.visual.fail=True
        self.assertEqual(self.reply('hello')['state'],'failed')
        self.assertEqual(self.app.pose,previous)
        self.assertTrue(previous[1].exists())

    def test_reset_during_capture_cannot_restore_pose_or_history(self):
        self.reply('wave')
        self.visual.after_capture=self.app.reset
        self.assertEqual(self.reply('hello')['state'],'cancelled')
        self.assertIsNone(self.app.pose)
        self.assertEqual(list(Path(self.temp.name).glob('*-pose.png')),[])
        self.assertEqual(self.app.store.snapshot()['turns'],[])

    def test_pose_capture_uses_decoded_frames_not_container_frame_estimate(self):
        from local_app.visual import PortraitRenderer
        renderer=PortraitRenderer.__new__(PortraitRenderer)
        renderer.cv=Mock()
        capture=renderer.cv.VideoCapture.return_value
        capture.read.side_effect=[(True,'first frame'),(True,'last frame'),(False,None)]
        renderer.cv.imwrite.return_value=True
        renderer.capture_last_frame(Path('fixture.mp4'),Path('pose.png'))
        renderer.cv.imwrite.assert_called_once_with('pose.png','last frame')
        capture.set.assert_not_called()
        capture.release.assert_called_once()

    def test_immediate_step_back_reuses_completed_approach_once(self):
        self.assertEqual(self.reply('closer')['state'],'done')
        cached = self.app.return_motion[1]
        self.assertTrue(cached.exists())
        returned = self.reply('farther')
        self.assertEqual(returned['state'],'done')
        self.assertEqual(self.generate.call_count,1)
        self.assertEqual(self.reverse.call_count,1)
        self.assertFalse(returned['chunks'][0]['render']['fresh_body_generation'])
        self.assertIsNone(self.app.return_motion)
        self.assertFalse(cached.exists())
        self.reply('farther')
        self.assertEqual(self.generate.call_count,2)

    def test_other_successful_video_invalidates_return_and_failed_turn_preserves_it(self):
        self.reply('closer')
        cached = self.app.return_motion
        self.visual.fail=True
        self.assertEqual(self.reply('farther')['state'],'failed')
        self.assertEqual(self.app.return_motion,cached)
        self.assertTrue(cached[1].exists())
        self.visual.fail=False
        self.reply('hello')
        self.assertIsNone(self.app.return_motion)
        self.assertFalse(cached[1].exists())

    def test_reset_during_approach_does_not_resurrect_return_media(self):
        self.visual.after_capture=self.app.reset
        self.assertEqual(self.reply('closer')['state'],'cancelled')
        self.assertIsNone(self.app.return_motion)
        self.assertEqual(list(Path(self.temp.name).glob('*-return.mp4')),[])


if __name__=='__main__':
    unittest.main()
