import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from local_app import motion
from local_app.models import Cancelled


class MotionBoundaryTests(unittest.TestCase):
    def test_invalid_action_never_submits_or_reads_reference(self):
        with patch.object(motion, 'request') as network, patch.object(motion.shutil, 'copyfile') as copy:
            with self.assertRaises(ValueError):
                motion.generate('fullbody', '../../anything', 2, threading.Event(), Path('unused.mp4'))
            network.assert_not_called()
            copy.assert_not_called()

    def test_already_cancelled_never_submits(self):
        event = threading.Event()
        event.set()
        with patch.object(motion, 'request') as network:
            with self.assertRaises(Cancelled):
                motion.generate('fullbody', 'wave', 2, event, Path('unused.mp4'))
            network.assert_not_called()

    def run_case(self, callback, exception=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root/'generated/local-app'
            assets.mkdir(parents=True)
            (assets/'fullbody.png').write_bytes(b'reference fixture')
            destination = root/'reply.mp4'
            with patch.object(motion, 'ROOT', root), patch.object(motion, 'CACHE', root/'cache'), patch.object(motion, 'request', side_effect=callback):
                with self.assertRaises(exception):
                    motion.generate('fullbody', 'wave', 2, self.event, destination)
            self.assertFalse(destination.exists())
            self.assertEqual(list((root/'cache/ComfyUI/input').iterdir()), [])

    def test_worker_cannot_read_outside_its_output_directory(self):
        self.event = threading.Event()
        def network(path, data=None):
            if path == '/prompt':
                return {'prompt_id':'ours'}
            return {'ours':{'status':{'status_str':'success'},'outputs':{'13':{'images':[
                {'filename':'private.mp4','subfolder':'../../..'}]}}}}
        self.run_case(network, RuntimeError)

    def test_cancel_interrupts_only_our_prompt(self):
        self.event = threading.Event()
        calls = []
        def network(path, data=None):
            calls.append((path,data))
            if path == '/prompt':
                self.event.set()
                return {'prompt_id':'ours'}
            return {}
        self.run_case(network, Cancelled)
        self.assertIn(('/queue',{'delete':['ours']}),calls)
        self.assertIn(('/interrupt',{'prompt_id':'ours'}),calls)
        self.assertFalse(any(data and data.get('clear') for _,data in calls))


if __name__ == '__main__':
    unittest.main()
