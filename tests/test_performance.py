import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from local_app.performance import load_reviewed_performance


class PerformanceAssetTests(unittest.TestCase):
    def test_review_and_every_asset_hash_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            names=['fullbody.png','performance-near.png','performance-closer.mp4','performance-farther.mp4']
            manifest={'version':1,'sha256':{}}
            for name in names:
                (folder/name).write_bytes(name.encode())
                manifest['sha256'][name]=hashlib.sha256(name.encode()).hexdigest()
            record=folder/'performance.json';record.write_text(json.dumps(manifest))
            self.assertEqual(load_reviewed_performance(folder),{})
            manifest['reviewed']=True;record.write_text(json.dumps(manifest))
            result=load_reviewed_performance(folder)
            self.assertEqual(result[('base','closer')]['to'],'near')
            self.assertEqual(result[('near','farther')]['to'],'base')
            for name in names:
                (folder/name).write_bytes(b'changed')
                self.assertEqual(load_reviewed_performance(folder),{})
                (folder/name).write_bytes(name.encode())

    def test_malformed_manifest_has_no_selected_motion(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for content in ['null','[]','{','{"version":1,"reviewed":true,"sha256":[]}']:
                (folder/'performance.json').write_text(content)
                self.assertEqual(load_reviewed_performance(folder),{})
