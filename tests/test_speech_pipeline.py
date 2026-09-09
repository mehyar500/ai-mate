from pathlib import Path
import tempfile
import threading
import time
import unittest

from local_app.engine import CompanionEngine
from local_app.models import Cancelled, check_cancel
from local_app.engine import SpeechPrefetch, speech_phrases

LONG = ('One, two, three, four, five, six, seven, eight, nine, ten. '
        'Eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen. '
        'Nineteen, twenty, twenty-one, twenty-two, twenty-three, twenty-four, twenty-five.')


class SpeechPipelineTests(unittest.TestCase):
    def test_words_and_punctuation_survive_long_replies(self):
        for text in (LONG, '  Hello.\nHow are you?  ', 'word' * 60, '', 'Price is 1.25 dollars. ' * 20):
            with self.subTest(text=text[:20]):
                self.assertEqual(' '.join(speech_phrases(text)), ' '.join(text.split()))
        self.assertGreater(len(speech_phrases(LONG)), 2)
        self.assertLessEqual(len(speech_phrases(LONG)[0]), 72)

    def test_one_ahead_synthesis_overlaps_consumer_and_stops_on_cancel(self):
        entered, release, cancel = threading.Event(), threading.Event(), threading.Event()
        class Models:
            def speech(self, text, path):
                if text == 'second':
                    entered.set()
                    release.wait(2)
                path.write_bytes(b'audio')
                return 1
        with tempfile.TemporaryDirectory() as folder:
            prefetch = SpeechPrefetch(Models(), ['first', 'second', 'third'], Path(folder), 'test', cancel)
            try:
                prefetch.take(0)
                self.assertTrue(entered.wait(1), 'Next speech was not prepared while the consumer works')
                cancel.set(); release.set()
                with self.assertRaises(Cancelled):
                    prefetch.take(1)
            finally:
                release.set(); prefetch.close()
            self.assertFalse((Path(folder) / 'test-2.wav').exists())

    def test_engine_finishes_all_phrases_and_performs_action_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = CompanionEngine(root)
            (root/'fullbody.png').write_bytes(b'image')
            (root/'approach.mp4').write_bytes(b'approach')
            (root/'near.mp4').write_bytes(b'near')
            app.performance = {('base', 'closer'): {'path': root/'approach.mp4', 'to': 'near'}}
            app.near_idle_video = root/'near.mp4'
            class Models:
                def __init__(self):
                    self.visual = self
                    self.sources = []
                    self.offsets = []
                def plan(self, *args):
                    return {'reply': LONG, 'presentation': 'video', 'scene': 'fullbody', 'action': 'closer', 'facts': []}
                def load_visual(self): return self
                def speech(self, text, path): path.write_bytes(b'audio'); return 1
                def render(self, audio, destination, event, scene, **kwargs):
                    self.sources.append(kwargs['motion_path'].read_bytes())
                    self.offsets.append(kwargs['motion_start_s'])
                    destination.write_bytes(b'video')
                    return {'duration_s': 1}
                def capture_last_frame(self, video, destination): destination.write_bytes(b'pose')
            app.models = Models(); app.ready = True
            key = app.submit('come closer', 'video', 'fullbody')
            deadline = time.monotonic() + 3
            while app.busy and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertFalse(app.busy)
            job = app.job(key)
            self.assertEqual(job['state'], 'done', job.get('error'))
            self.assertEqual(' '.join(chunk['text'] for chunk in job['chunks']), LONG)
            self.assertEqual(app.store.snapshot()['turns'][0]['assistant'], LONG)
            self.assertEqual(app.models.sources, [b'approach'] + [b'near']*(len(job['chunks'])-1))
            self.assertEqual(app.models.offsets, [0] + list(range(len(job['chunks'])-1)))
            self.assertEqual(job['prepared_pose'], 'near')

    def test_engine_cancel_joins_prefetch_before_removing_media(self):
        entered, release = threading.Event(), threading.Event()
        class Models:
            def __init__(self): self.visual = self; self.calls = 0
            def plan(self, *args):
                return {'reply':LONG, 'presentation':'video', 'scene':'fullbody', 'action':'none', 'facts':[]}
            def load_visual(self): return self
            def speech(self, phrase, path):
                self.calls += 1
                if self.calls == 2:
                    entered.set(); release.wait(2)
                path.write_bytes(b'audio')
                return 1
            def render(self, audio, destination, event, scene, **kwargs):
                while not event.wait(.01): pass
                check_cancel(event)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); app = CompanionEngine(root)
            (root/'fullbody.png').write_bytes(b'image')
            (root/'idle.mp4').write_bytes(b'idle'); app.idle_video = root/'idle.mp4'
            app.models = Models(); app.ready = True
            key = app.submit('hello', 'video', 'fullbody')
            try:
                self.assertTrue(entered.wait(1))
                app.cancel(key)
                self.assertTrue(app.busy)
            finally:
                release.set()
                deadline = time.monotonic() + 3
                while app.busy and time.monotonic() < deadline: time.sleep(.01)
            self.assertFalse(app.busy)
            self.assertEqual(app.job(key)['state'], 'cancelled')
            self.assertEqual(app.store.snapshot()['turns'], [])
            self.assertEqual(list(root.glob(key+'-*')), [])


if __name__ == '__main__': unittest.main()
