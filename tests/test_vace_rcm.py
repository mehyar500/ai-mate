"""CPU checks for the isolated renderer's numerical compatibility boundaries."""
import importlib.util
import unittest

from scripts.benchmark_vace import dense_attention
from scripts.vace_rcm import body_control_bounds, schedule, transfer_generator


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Requires optional PyTorch')
class VaceRcmTests(unittest.TestCase):
    def test_body_region_uses_both_portrait_dimensions(self):
        import numpy as np
        points = np.full((2, 134, 2), .5)
        points[0, 0], points[1, 0] = [.1, .2], [.8, .9]
        bounds = body_control_bounds(points, np.ones(134), (200, 400))
        self.assertEqual(bounds[:2], (8, 56))
        self.assertTrue(172 <= bounds[2] <= 173)
        self.assertEqual(bounds[3], 384)
        for size in [(0, 400), (200, float('nan')), (-1, 400)]:
            with self.assertRaises(ValueError):
                body_control_bounds(points, np.ones(134), size)

    def test_body_region_contains_motion_without_uncertain_landmarks(self):
        import numpy as np
        points = np.full((3, 134, 2), .5)
        points[1, 2] = [.1, .2]
        points[2, 4] = [.8, .9]
        points[:, 133] = [-1, -1]
        scores = np.ones(134)
        scores[133] = 0
        left, top, right, bottom = body_control_bounds(points, scores, 100)
        self.assertEqual((left, top, bottom), (4, 14, 96))
        self.assertTrue(86 <= right <= 87)  # Conservative floating-point ceil.
        with self.assertRaises(ValueError):
            body_control_bounds(points, scores * 0, 100)

    def test_patch_conversion_matches_linear_patchification(self):
        import torch
        from torch.nn import functional as F
        torch.manual_seed(5)
        image = torch.randn(1, 2, 3, 4, 6, dtype=torch.float64)
        weight = torch.randn(7, 8, dtype=torch.float64)
        bias = torch.randn(7, dtype=torch.float64)
        control = torch.randn(2)
        original = {'patch_embedding.weight': torch.zeros(7, 2, 1, 2, 2),
                    'patch_embedding.bias': torch.zeros(7), 'vace_blocks.0.weight': control}
        result, evidence = transfer_generator(original, {'net.patch_embedding.weight': weight,
                                                         'net.patch_embedding.bias': bias})
        patches = image.reshape(1, 2, 3, 1, 2, 2, 3, 2).permute(0, 2, 4, 6, 1, 3, 5, 7).reshape(1, 18, 8)
        expected = F.linear(patches, weight, bias)
        actual = F.conv3d(image, result['patch_embedding.weight'], result['patch_embedding.bias'], stride=(1, 2, 2))
        torch.testing.assert_close(actual.flatten(2).transpose(1, 2), expected)
        self.assertIs(result['vace_blocks.0.weight'], control)
        self.assertEqual(evidence['replaced_base_tensors'], 2)
        self.assertEqual(original['patch_embedding.weight'].ndim, 5)
        self.assertEqual(weight.ndim, 2)

    def test_rejects_partial_unknown_duplicate_and_nonfinite_weights(self):
        import torch
        base = {'a': torch.zeros(2), 'b': torch.zeros(2), 'vace_blocks.c': torch.ones(1)}
        for state in [{'a': torch.ones(2)}, {'a': torch.ones(2), 'c': torch.ones(2)},
                      {'a': torch.ones(2), 'net.a': torch.ones(2), 'b': torch.ones(2)},
                      {'a': torch.tensor([float('nan'), 0]), 'b': torch.ones(2)},
                      {'a': torch.ones(3), 'b': torch.ones(2)}]:
            with self.assertRaises(ValueError):
                transfer_generator(base, state)

    def test_schedule_matches_upstream_values(self):
        import math
        import torch
        for n in (1, 2, 4):
            expected = [80 / 81, *[math.tan(x) / (1 + math.tan(x)) for x in [1.5, 1.4, 1.0][:n - 1]], 0.]
            torch.testing.assert_close(schedule(n, 'cpu'), torch.tensor(expected, dtype=torch.float64))
        with self.assertRaises(ValueError):
            schedule(30, 'cpu')

    def test_only_known_scalar_training_counters_are_excluded(self):
        import torch
        state = {'a': torch.ones(2), 'net.accum_iteration': torch.tensor(-23)}
        result, evidence = transfer_generator({'a': torch.zeros(2)}, state)
        self.assertEqual(set(result), {'a'})
        self.assertEqual(evidence['discarded_training_counters'], ['accum_iteration'])
        for invalid in [torch.ones(2), torch.tensor(float('inf'))]:
            state['net.accum_iteration'] = invalid
            with self.assertRaisesRegex(ValueError, 'counter'):
                transfer_generator({'a': torch.zeros(2)}, state)

    def test_attention_matches_sdpa_and_rejects_truncation(self):
        import torch
        torch.manual_seed(11)
        q, k, v = torch.randn(1, 4, 2, 8), torch.randn(1, 6, 2, 8), torch.randn(1, 6, 2, 8)
        actual = dense_attention(q, k, v, q_lens=torch.tensor([4]), k_lens=torch.tensor([6]))
        expected = torch.nn.functional.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2))
        torch.testing.assert_close(actual, expected.transpose(1, 2))
        for lens in [{'q_lens': torch.tensor([3])}, {'k_lens': torch.tensor([5])}]:
            with self.assertRaisesRegex(ValueError, 'Padded'):
                dense_attention(q, k, v, **lens)


if __name__ == '__main__':
    unittest.main()
