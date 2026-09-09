"""State/lifecycle checks; neural image quality is tested separately on the GPU."""
from pathlib import Path
import tempfile
import threading
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
        self.render_options=[]

    def prepare(self, scene, reference_path=None):
        self.prepared.append(reference_path.read_bytes() if reference_path else None)

    def render(self, audio, destination, event, scene, **kwargs):
        self.render_options.append(kwargs)
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
        self.last_snapshot=snapshot
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

    def test_prepared_idle_only_applies_to_unchanged_base_pose(self):
        asset=Path(self.temp.name)/'idle-fullbody.mp4';asset.write_bytes(b'idle')
        self.app.idle_video=asset
        job=self.reply('hello')
        self.assertEqual(job['chunks'][0]['render']['motion_source'],'prepared_listening_loop')
        self.assertIsNone(self.app.pose)
        self.assertEqual(self.app.status()['idle_video'],'/idle/fullbody.mp4')
        self.reply('closer')
        self.assertIsNone(self.app.status()['idle_video'])
        job=self.reply('hello')
        self.assertNotIn('motion_source',job['chunks'][0]['render'])
        self.assertTrue(asset.exists())

    def install_performance(self):
        folder=Path(self.temp.name)
        for name in ['closer','farther','idle-base','idle-near']:
            (folder/(name+'.mp4')).write_bytes(name.encode())
        self.app.idle_video=folder/'idle-base.mp4'
        self.app.near_idle_video=folder/'idle-near.mp4'
        self.app.performance={('base','closer'):{'path':folder/'closer.mp4','to':'near'},
                              ('near','farther'):{'path':folder/'farther.mp4','to':'base'}}

    def test_reviewed_pose_survives_conversation_before_return(self):
        self.install_performance()
        closer=self.reply('closer')
        self.assertEqual(closer['prepared_pose'],'near')
        self.assertEqual(closer['idle_video'],'/idle/near.mp4')
        self.assertEqual(closer['chunks'][0]['render']['motion_source'],'reviewed_prepared_transition')
        self.assertIsNone(self.app.return_motion)
        hello=self.reply('hello')
        self.assertEqual(hello['chunks'][0]['render']['motion_source'],'prepared_listening_loop')
        self.assertEqual(hello['prepared_pose'],'near')
        self.assertEqual(self.app.models.last_snapshot['visual_pose'],'near')
        self.assertNotIn('visual_pose',self.app.store.snapshot())
        farther=self.reply('farther')
        self.assertEqual(farther['prepared_pose'],'base')
        self.assertEqual(farther['idle_video'],'/idle/fullbody.mp4')
        self.generate.assert_not_called();self.reverse.assert_not_called()

    def test_partial_pose_survives_speech_then_continues_or_reverses(self):
        self.install_performance()
        self.app.scene = 'fullbody'
        for command, offset, destination in [('closer', 1.2, 'near'), ('farther', 1.8, 'base')]:
            self.app.performance_state = None
            self.app.visual_cursor = .4
            pose = Path(self.temp.name)/'stopped.png'; pose.write_bytes(b'stopped pose')
            self.app.pose = ('fullbody', pose)
            ordinary = self.reply('hello')
            self.assertEqual(ordinary['state'], 'done')
            self.assertEqual(self.app.visual_cursor, .4)
            with patch('local_app.playback.video_duration', return_value=3):
                movement = self.reply(command)
            self.assertEqual(movement['state'], 'done', movement.get('error'))
            self.assertAlmostEqual(self.visual.render_options[-1]['motion_start_s'], offset)
            self.assertEqual(self.app.performance_state, destination)
            self.assertIsNone(self.app.visual_cursor)
        self.generate.assert_not_called(); self.reverse.assert_not_called()

    def test_failed_or_reset_transition_cannot_commit_a_prepared_pose(self):
        self.install_performance()
        self.visual.fail=True
        self.assertEqual(self.reply('closer')['state'],'failed')
        self.assertEqual(self.app.performance_state,'base')
        self.visual.fail=False;self.visual.after_capture=self.app.reset
        self.assertEqual(self.reply('closer')['state'],'cancelled')
        self.assertEqual(self.app.performance_state,'base')
        self.assertIsNone(self.app.pose)

    def test_unreviewed_action_invalidates_known_pose(self):
        self.install_performance()
        self.reply('closer')
        self.reply('wave')
        self.assertIsNone(self.app.performance_state)
        self.assertIsNone(self.app.status()['idle_video'])
        self.reply('farther')
        self.assertEqual(self.generate.call_count,2)

    def test_reviewed_wave_returns_to_base_and_is_never_used_from_near_or_partial(self):
        self.install_performance()
        wave = Path(self.temp.name)/'wave.mp4'; wave.write_bytes(b'wave')
        self.app.performance[('base','wave')] = {'path':wave,'from':'base','to':'base','kind':'gesture'}
        job = self.reply('wave')
        self.assertEqual(job['state'],'done')
        self.assertEqual(job['prepared_pose'],'base')
        self.assertEqual(job['idle_video'],'/idle/fullbody.mp4')
        self.assertFalse(job['chunks'][0]['render']['fresh_body_generation'])
        self.generate.assert_not_called()
        self.reply('closer')
        self.reply('wave')
        self.assertEqual(self.generate.call_count,1)
        self.app.performance_state = None
        self.app.visual_cursor = .4
        self.reply('wave')
        self.assertEqual(self.generate.call_count,2)
        self.assertIsNone(self.app.performance_state)
        self.assertIsNone(self.app.visual_cursor)

    def test_near_wave_preserves_close_listening_and_return_path(self):
        self.install_performance()
        wave=Path(self.temp.name)/'near-wave.mp4';wave.write_bytes(b'near wave')
        self.app.performance[('near','wave')]={'path':wave,'from':'near','to':'near','kind':'gesture'}
        self.reply('closer')
        job=self.reply('wave')
        self.assertEqual(job['state'],'done')
        self.assertEqual(job['prepared_pose'],'near')
        self.assertEqual(job['idle_video'],'/idle/near.mp4')
        self.assertFalse(job['chunks'][0]['render']['fresh_body_generation'])
        self.assertEqual(self.visual.render_options[-1]['motion_start_s'],0)
        hello=self.reply('hello')
        self.assertEqual(hello['prepared_pose'],'near')
        self.assertEqual(hello['chunks'][0]['render']['motion_source'],'prepared_listening_loop')
        self.assertEqual(self.reply('farther')['prepared_pose'],'base')
        self.generate.assert_not_called();self.reverse.assert_not_called()

    def test_only_listening_footage_loops_beyond_source_duration(self):
        from local_app.visual import PortraitRenderer
        class Frame:
            shape=(2,2,3)
        frames=[Frame() for _ in range(4)]
        renderer=PortraitRenderer.__new__(PortraitRenderer)
        renderer.cv=Mock();renderer.np=Mock()
        capture=renderer.cv.VideoCapture.return_value
        capture.get.return_value=2
        for looping,expected in [(False,[0,1,2,3,3,3]),(True,[0,1,2,3,0,1])]:
            capture.read.side_effect=[(True,f) for f in frames]+[(False,None)]
            result=renderer.motion_frames(Path('fixture.mp4'),6,2,threading.Event(),lip_frames=0,loop=looping)
            self.assertEqual([frames.index(row[0]) for row in result],expected)

    def test_prepared_frame_cache_is_content_based_bounded_and_opt_in(self):
        from local_app.visual import PortraitRenderer
        class Frame:
            shape=(2,2,3)
        renderer=PortraitRenderer.__new__(PortraitRenderer)
        renderer.cv=Mock();renderer.np=Mock()
        capture=renderer.cv.VideoCapture.return_value
        capture.get.return_value=2
        event=threading.Event()
        folder=Path(self.temp.name)
        def read(name, content, reuse=True):
            path=folder/name;path.write_bytes(content)
            capture.read.side_effect=[(True,Frame()),(True,Frame()),(False,None)]
            renderer.motion_frames(path,2,2,event,lip_frames=0,reuse=reuse)
        read('first.mp4',b'base')
        self.assertFalse(renderer.motion_cache_hit)
        read('copy.mp4',b'base')
        self.assertTrue(renderer.motion_cache_hit)
        self.assertEqual(renderer.cv.VideoCapture.call_count,1)
        renderer.face_shift=-.04
        read('copy.mp4',b'base')
        self.assertFalse(renderer.motion_cache_hit)  # Crop tuning must rebuild face latents.
        read('copy.mp4',b'changed')
        self.assertFalse(renderer.motion_cache_hit)
        read('third.mp4',b'near')
        read('fourth.mp4',b'farther')
        read('fifth.mp4',b'closer')
        self.assertEqual(len(renderer._motion_cache),6)
        read('sixth.mp4',b'wave')
        self.assertEqual(len(renderer._motion_cache),6)
        read('seventh.mp4',b'near wave')
        self.assertEqual(len(renderer._motion_cache),6)
        read('first.mp4',b'base')
        self.assertFalse(renderer.motion_cache_hit)  # Oldest content was evicted.
        read('first.mp4',b'base',reuse=False)
        self.assertFalse(renderer.motion_cache_hit)
        self.assertIsNone(renderer._appearance_latents)

    def test_next_phrase_continues_the_listening_loop_phase(self):
        from local_app.visual import PortraitRenderer
        class Frame:
            shape = (2, 2, 3)
        frames = [Frame() for _ in range(4)]
        renderer = PortraitRenderer.__new__(PortraitRenderer)
        renderer.cv = Mock(); renderer.np = Mock()
        capture = renderer.cv.VideoCapture.return_value
        capture.get.return_value = 2
        capture.read.side_effect = [(True, f) for f in frames] + [(False, None)]
        rows = renderer.motion_frames(Path('fixture.mp4'), 4, 2, threading.Event(),
                                      lip_frames=0, loop=True, start_s=1.5)
        self.assertEqual([frames.index(row[0]) for row in rows], [3, 0, 1, 2])
        for offset in [-1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                renderer.motion_frames(Path('fixture.mp4'), 4, 2, threading.Event(), start_s=offset)


if __name__=='__main__':
    unittest.main()
