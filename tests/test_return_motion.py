"""Bounded reverse-video behavior; optional CPU FFmpeg integration uses synthetic frames."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from local_app.models import Cancelled
from local_app.motion import reverse_approach


class ReturnMotionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.folder=self.root/'generated/local-app'
        self.folder.mkdir(parents=True)
        self.source=self.folder/('a'*32+'-0-return.mp4')
        self.destination=self.folder/('b'*32+'-0-motion.mp4')
        self.root_patch=patch('local_app.motion.ROOT',self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def test_outside_paths_and_cancel_fail_before_starting_encoder(self):
        with patch('local_app.motion.subprocess.run') as probe:
            with self.assertRaises(ValueError):
                reverse_approach(self.root/'outside-return.mp4',self.destination,threading.Event())
            event=threading.Event();event.set()
            with self.assertRaises(Cancelled):
                reverse_approach(self.source,self.destination,event)
            probe.assert_not_called()

    def test_long_clip_is_rejected_without_starting_reverse(self):
        self.source.write_bytes(b'synthetic')
        metadata={'streams':[{'duration':'30','width':384,'height':576,'nb_frames':'720'}]}
        with patch('local_app.motion.subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps(metadata).encode())), patch('local_app.motion.subprocess.Popen') as encoder:
            with self.assertRaises(ValueError):
                reverse_approach(self.source,self.destination,threading.Event())
            encoder.assert_not_called()

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'CPU FFmpeg not installed')
    def test_real_reverse_swaps_first_and_last_frames(self):
        frames=b''.join(bytes([20+i*4])*16*16*3 for i in range(48))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                        '-s','16x16','-r','24','-i','pipe:0','-an','-c:v','libx264','-crf','0',str(self.source)],
                       input=frames,capture_output=True,check=True,timeout=10,
                       creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        metrics=reverse_approach(self.source,self.destination,threading.Event())
        decoded=subprocess.run(['ffmpeg','-v','error','-i',str(self.destination),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
                               capture_output=True,check=True,timeout=10,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout
        frame_size=16*16*3
        self.assertEqual(len(decoded),48*frame_size)
        self.assertLess(abs(sum(decoded[:frame_size])/frame_size-208),4)
        self.assertLess(abs(sum(decoded[-frame_size:])/frame_size-20),4)
        self.assertFalse(metrics['fresh_body_generation'])
        self.assertEqual(metrics['motion_frames'],48)


if __name__=='__main__':unittest.main()
