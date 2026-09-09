"""Offline review coverage and data/markup boundaries; no GPU or browser needed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_call_review import build, json_script, reviewed_media


class CallReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.identifier='a'*32
        self.media=self.root/(self.identifier+'-0.mp4');self.media.write_bytes(b'synthetic-test-bytes')
        self.item={'id':self.identifier,'chunk':0,'video_sha256':hashlib.sha256(self.media.read_bytes()).hexdigest(),
                   'summary':{'decoded_frames':1,'fps':20,'flagged_frames':[]},'frames':[{'time_s':0}]}
        self.row={'id':self.identifier,'case':'synthetic','expected':{'prompt':'</script><script>alert(1)</script>'},
                  'job':{'text':'Neutral synthetic reply','chunks':[{'index':0}]}}
        self.write('qualification.json',{'results':[self.row]})
        self.write('summary.json',{'turns':1})
        self.write('frame-review.json',{'reviews':[self.item]})

    def write(self,name,value):
        (self.root/name).write_text(json.dumps(value))

    def test_text_cannot_end_the_inert_data_element(self):
        encoded=json_script({'text':'</script><img src=x onerror=alert(1)>&'})
        self.assertNotIn('<',encoded);self.assertNotIn('&',encoded)
        self.assertEqual(json.loads(encoded)['text'],'</script><img src=x onerror=alert(1)>&')

    def test_hash_change_and_path_escape_fail(self):
        self.assertEqual(reviewed_media(self.root,self.item),self.media.name)
        self.media.write_bytes(b'changed')
        with self.assertRaises(ValueError):reviewed_media(self.root,self.item)
        with self.assertRaises(ValueError):reviewed_media(self.root,{**self.item,'id':'../../outside'})

    def test_report_covers_the_audit_and_keeps_dialogue_inert(self):
        result=build(self.root)
        self.assertEqual((result['clips'],result['frames']),(1,1))
        page=Path(result['output']).read_text(encoding='utf-8')
        self.assertNotIn(self.row['expected']['prompt'],page)
        self.assertIn('Content-Security-Policy',page)
        self.assertNotIn('type="checkbox" checked',page)

    def test_partial_and_duplicate_audits_fail(self):
        for rows in [[],[self.item,self.item]]:
            self.write('frame-review.json',{'reviews':rows})
            with self.assertRaises(ValueError):build(self.root)
        self.write('frame-review.json',{'reviews':[self.item]})
        self.write('summary.json',{'turns':2})
        with self.assertRaises(ValueError):build(self.root)

    def test_missing_media_is_reported_instead_of_omitted(self):
        self.write('frame-review.json',{'reviews':[{**self.item,'media_missing':True}]})
        with self.assertRaises(ValueError):build(self.root)


if __name__=='__main__':unittest.main()
