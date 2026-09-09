"""Optional numerical/format checks for the isolated S2 renderer adapter."""
import importlib.util
from pathlib import Path
import sys
import unittest

from scripts.longlive2_s2 import load_dequantizer, unpack_checkpoint, verify_numeric_fixture

CODE = Path(__file__).resolve().parents[1] / '.cache/local-poc/LongLive2'
AVAILABLE = importlib.util.find_spec('torch') is not None and (CODE / 'fouroversix/src/fouroversix').is_dir()


@unittest.skipUnless(AVAILABLE, 'Requires optional local LongLive checkout and PyTorch')
class S2AdapterTests(unittest.TestCase):
    @staticmethod
    def checkpoint():
        import torch
        buffers = {'values': torch.full((128, 32), 0x71, dtype=torch.uint8),
                   'scale_factors': torch.ones(512, dtype=torch.float8_e4m3fn),
                   'amax': torch.tensor([1536.]),
                   'metadata': torch.tensor([128, 64, 128, 64], dtype=torch.int32)}
        return {'checkpoint_format': 'longlive_generator_nvfp4', 'checkpoint_version': 1,
                'merged_lora': True, 'model_name': 'Wan2.2-TI2V-5B',
                'quantization': {'format': 'nvfp4', 'backend': 'fouroversix', 'materialized': True,
                                 'dtype': 'bfloat16', 'weight_scale_rule': 'mse'},
                'generator': {f'layer{i}.quantized_weight_{suffix}': value
                              for i in range(300) for suffix, value in buffers.items()}}

    def test_all_codes_and_import_cleanup(self):
        result = verify_numeric_fixture(load_dequantizer(CODE))
        self.assertTrue(all(result.values()))
        self.assertFalse(any(n == 'fouroversix' or n.startswith('fouroversix.') for n in sys.modules))

    def test_full_conversion_preserves_source_and_values(self):
        import torch
        original = self.checkpoint()
        state, evidence = unpack_checkpoint(original, CODE)
        self.assertEqual(len(original['generator']), 1200)
        self.assertEqual(len(state), 300)
        weight = state['layer299.weight']
        self.assertEqual(weight.dtype, torch.bfloat16)
        self.assertTrue(torch.all(weight[:, ::2] == .5))
        self.assertTrue(torch.all(weight[:, 1::2] == 6.))
        self.assertEqual(evidence['converted_linear_layers'], 300)
        self.assertFalse(evidence['native_nvfp4'])

    def test_rejects_wrong_scale_rule(self):
        data = self.checkpoint()
        data['quantization']['weight_scale_rule'] = 'static_6'
        with self.assertRaisesRegex(ValueError, 'quantization settings'):
            unpack_checkpoint(data, CODE)

    def test_rejects_missing_and_conflicting_buffers(self):
        data = self.checkpoint()
        del data['generator']['layer0.quantized_weight_metadata']
        with self.assertRaisesRegex(ValueError, 'Incomplete or conflicting'):
            unpack_checkpoint(data, CODE)
        data = self.checkpoint()
        data['generator']['layer0.weight'] = data['generator']['layer0.quantized_weight_values']
        with self.assertRaisesRegex(ValueError, 'Incomplete or conflicting'):
            unpack_checkpoint(data, CODE)

    def test_rejects_bad_layout_and_nonfinite_scale(self):
        import torch
        for suffix, value in [('metadata', torch.tensor([128, 64, 127, 64], dtype=torch.int32)),
                              ('amax', torch.tensor([float('nan')]))]:
            data = self.checkpoint()
            data['generator']['layer0.quantized_weight_' + suffix] = value
            with self.assertRaisesRegex(ValueError, 'tensor layout'):
                unpack_checkpoint(data, CODE)


if __name__ == '__main__':
    unittest.main()
