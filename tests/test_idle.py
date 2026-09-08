import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from local_app.idle import load_reviewed_idle


class IdleAssetTests(unittest.TestCase):
    def test_only_reviewed_matching_asset_and_reference_load(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/'fullbody.png').write_bytes(b'reference')
            video=folder/'idle-fullbody.mp4';video.write_bytes(b'video')
            manifest={'version':1,'scene':'fullbody','sha256':hashlib.sha256(b'video').hexdigest(),
                      'reference_sha256':hashlib.sha256(b'reference').hexdigest()}
            record=folder/'idle-fullbody.json'
            record.write_text(json.dumps(manifest))
            self.assertIsNone(load_reviewed_idle(folder))
            manifest['reviewed']=True;record.write_text(json.dumps(manifest))
            self.assertEqual(load_reviewed_idle(folder),video)
            video.write_bytes(b'changed')
            self.assertIsNone(load_reviewed_idle(folder))
            video.write_bytes(b'video');(folder/'fullbody.png').write_bytes(b'new identity')
            self.assertIsNone(load_reviewed_idle(folder))

    def test_missing_or_malformed_manifest_falls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            self.assertIsNone(load_reviewed_idle(folder))
            for content in ['[]','null','{','1']:
                (folder/'idle-fullbody.json').write_text(content)
                self.assertIsNone(load_reviewed_idle(folder))
