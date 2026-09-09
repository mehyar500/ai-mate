"""ASR device selection must be explicit, offline and recoverable."""
import tempfile
import unittest
from pathlib import Path
from local_app.models import recognition_settings
from local_app.engine import configure_runtime


class RecognitionDeviceTests(unittest.TestCase):
    def test_portable_cpu_default_and_qualified_gpu_precision(self):
        cpu=recognition_settings({});gpu=recognition_settings({'AI_MATE_ASR_DEVICE':'cuda'})
        self.assertEqual((cpu['device'],cpu['compute_type']),('cpu','int8'))
        self.assertEqual((gpu['device'],gpu['compute_type']),('cuda','float16'))
        self.assertTrue(cpu['local_files_only'] and gpu['local_files_only'])
        self.assertEqual(gpu['num_workers'],1)

    def test_unknown_device_never_silently_selects_a_backend(self):
        for value in ['', 'auto', 'remote', '../../cuda', 'CUDA']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                recognition_settings({'AI_MATE_ASR_DEVICE':value})

    def test_local_setting_loads_but_explicit_cpu_recovery_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env';path.write_text('AI_MATE_ASR_DEVICE=cuda\nUNRELATED_SECRET=ignored\n')
            selected={};configure_runtime(path,selected)
            self.assertEqual(selected,{'AI_MATE_ASR_DEVICE':'cuda'})
            recovery={'AI_MATE_ASR_DEVICE':'cpu'};configure_runtime(path,recovery)
            self.assertEqual(recognition_settings(recovery)['device'],'cpu')


if __name__=='__main__':unittest.main()
