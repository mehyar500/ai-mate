"""Offline provenance checks; GPU execution is covered by isolated benchmarks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from local_app.trt_decoder import verified_engine_bytes
from local_app.visual import PortraitRenderer


class DecoderProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.engine=self.folder/'decoder.engine';self.engine.write_bytes(b'synthetic-engine')
        self.versions={'tensorrt':'synthetic-version','gpu':'synthetic-gpu','torch':'synthetic-torch'}
        self.sources={'config.json':'synthetic-config','diffusion_pytorch_model.safetensors':'synthetic-weights'}
        self.record=self.folder/'build.json'
        self.manifest={**self.versions,'reviewed':True,'source_vae_sha256':self.sources,
                       'engine_sha256':hashlib.sha256(self.engine.read_bytes()).hexdigest()}
        self.save()

    def save(self):
        self.record.write_text(json.dumps(self.manifest))

    def read(self):
        return verified_engine_bytes(self.folder,self.versions,self.sources)

    def test_exact_reviewed_local_build_is_accepted(self):
        self.assertEqual(self.read(),b'synthetic-engine')

    def test_missing_and_non_boolean_review_are_rejected(self):
        for value in [None,False,'true',1]:
            self.manifest['reviewed']=value;self.save()
            with self.assertRaises(ValueError):self.read()

    def test_changed_engine_or_source_cannot_load(self):
        self.engine.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.read()
        self.engine.write_bytes(b'synthetic-engine')
        self.manifest['source_vae_sha256']={};self.save()
        with self.assertRaises(ValueError):self.read()

    def test_gpu_runtime_and_torch_changes_require_a_matching_build(self):
        for key in self.versions:
            original=self.manifest[key];self.manifest[key]='different';self.save()
            with self.assertRaises(ValueError):self.read()
            self.manifest[key]=original

    def test_missing_empty_oversized_and_malformed_artifacts_fail(self):
        self.engine.write_bytes(b'')
        with self.assertRaises(ValueError):self.read()
        self.engine.write_bytes(b'synthetic-engine')
        for value in ['null','[]','{',' '*16385]:
            self.record.write_text(value)
            with self.assertRaises(ValueError):self.read()
        self.record.unlink()
        with self.assertRaises(OSError):self.read()

    def test_unreviewed_allowance_is_explicit_and_still_checks_hashes(self):
        self.manifest['reviewed']=False;self.save()
        self.assertEqual(verified_engine_bytes(self.folder,self.versions,self.sources,require_review=False),b'synthetic-engine')
        self.engine.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            verified_engine_bytes(self.folder,self.versions,self.sources,require_review=False)

    def test_unknown_backend_fails_before_gpu_initialization(self):
        with self.assertRaises(ValueError):PortraitRenderer(decoder_backend='unknown')
