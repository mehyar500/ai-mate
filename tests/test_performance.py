import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from local_app.media import load_reviewed_performance, load_reviewed_wave


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
            near=folder/'performance-near-wave.mp4';near.write_bytes(b'near wave')
            near_record=folder/'performance-near-wave.json'
            near_manifest={'version':1,'reviewed':True,'pose':'near','sha256':{
                'performance-near.png':manifest['sha256']['performance-near.png'],
                near.name:hashlib.sha256(near.read_bytes()).hexdigest()}}
            near_record.write_text(json.dumps(near_manifest))
            self.assertEqual(load_reviewed_performance(folder)[('near','wave')]['to'],'near')
            near.write_bytes(b'changed')
            result=load_reviewed_performance(folder)
            self.assertNotIn(('near','wave'),result)
            self.assertIn(('base','closer'),result)
            self.assertIn(('near','farther'),result)
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

    def test_wave_needs_separate_review_matching_reference_and_unchanged_media(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            media = folder/'performance-wave.mp4'; media.write_bytes(b'wave')
            record = folder/'performance-wave.json'
            manifest = {'version':1,'reviewed':True,'sha256':{
                'fullbody.png':'reference','performance-wave.mp4':hashlib.sha256(b'wave').hexdigest()}}
            record.write_text(json.dumps(manifest))
            self.assertEqual(load_reviewed_wave(folder,'reference')['kind'],'gesture')
            self.assertIsNone(load_reviewed_wave(folder,'different identity'))
            manifest['reviewed'] = False; record.write_text(json.dumps(manifest))
            self.assertIsNone(load_reviewed_wave(folder,'reference'))
            manifest['reviewed'] = True; record.write_text(json.dumps(manifest))
            media.write_bytes(b'changed')
            self.assertIsNone(load_reviewed_wave(folder,'reference'))
            record.write_text('null')
            self.assertIsNone(load_reviewed_wave(folder,'reference'))

    def test_near_wave_requires_its_own_pose_review_and_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            media=folder/'performance-near-wave.mp4';media.write_bytes(b'near wave')
            record=folder/'performance-near-wave.json'
            manifest={'version':1,'reviewed':True,'pose':'near','sha256':{
                'performance-near.png':'near reference',media.name:hashlib.sha256(media.read_bytes()).hexdigest()}}
            record.write_text(json.dumps(manifest))
            result=load_reviewed_wave(folder,'near reference',pose='near')
            self.assertEqual((result['from'],result['to'],result['kind']),('near','near','gesture'))
            self.assertIsNone(load_reviewed_wave(folder,'base reference',pose='near'))
            self.assertIsNone(load_reviewed_wave(folder,'near reference',pose='base'))
            self.assertIsNone(load_reviewed_wave(folder,'near reference',pose='../near'))
            for field,value in [('pose','base'),('pose',None),('reviewed',False)]:
                changed={**manifest,field:value};record.write_text(json.dumps(changed))
                self.assertIsNone(load_reviewed_wave(folder,'near reference',pose='near'))
            record.write_text(json.dumps(manifest));media.write_bytes(b'changed')
            self.assertIsNone(load_reviewed_wave(folder,'near reference',pose='near'))
