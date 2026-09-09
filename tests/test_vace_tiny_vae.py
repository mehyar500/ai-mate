"""Layout/range and state isolation boundaries for the optional tiny decoder."""
import importlib.util
import unittest
from unittest.mock import Mock

from scripts.vace_tiny_vae import TinyWanVAE


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Requires optional PyTorch')
class TinyVaeTests(unittest.TestCase):
    def setUp(self):
        self.adapter = object.__new__(TinyWanVAE)
        self.adapter.device = 'cpu'
        self.adapter.model = Mock()

    def test_encode_maps_rgb_layout_and_range(self):
        import torch
        rgb = torch.linspace(-1, 1, 3 * 5 * 8 * 16).reshape(3, 5, 8, 16)
        encoded = torch.randn(1, 2, 16, 1, 2)
        self.adapter.model.encode_video.return_value = encoded
        result = self.adapter.encode([rgb])[0]
        actual = self.adapter.model.encode_video.call_args.args[0]
        self.assertEqual(actual.shape, (1, 5, 3, 8, 16))
        self.assertEqual((float(actual.min()), float(actual.max())), (0., 1.))
        torch.testing.assert_close(actual, ((rgb.permute(1, 0, 2, 3)[None].half() + 1) * .5))
        torch.testing.assert_close(result, encoded[0].permute(1, 0, 2, 3))

    def test_decode_does_not_apply_wan_scaling_twice(self):
        import torch
        latent = torch.linspace(-5, 5, 16 * 2 * 2 * 3).reshape(16, 2, 2, 3)
        decoded = torch.rand(1, 5, 3, 16, 24)
        self.adapter.model.decode_video.return_value = decoded
        result = self.adapter.decode([latent])[0]
        actual = self.adapter.model.decode_video.call_args.args[0]
        torch.testing.assert_close(actual, latent.permute(1, 0, 2, 3)[None].half())
        torch.testing.assert_close(result, decoded[0].permute(1, 0, 2, 3) * 2 - 1)

    def test_rejects_invalid_tensor_without_calling_model(self):
        import torch
        for value in [torch.zeros(3, 1, 2, 2), torch.zeros(16, 0, 2, 2),
                      torch.zeros(16, 1, 2, 2, dtype=torch.int32),
                      torch.full((16, 1, 2, 2), float('nan'))]:
            with self.assertRaises(ValueError):
                self.adapter.decode([value])
        self.adapter.model.decode_video.assert_not_called()
        self.assertEqual(self.adapter.decode([]), [])

    def test_stream_reset_and_cancellation_preserve_callers_mode(self):
        import torch
        instances = []

        class Stream:
            def __init__(self, model):
                instances.append(self)
                self.count = 0

            def decode(self, value=None):
                if value is None:
                    return None
                self.count += 1
                return torch.full((1, 1, 3, 8, 8), self.count / 10.)

        self.adapter.streaming_type = Stream
        latent = torch.zeros(16, 1, 1, 1)
        with torch.enable_grad():
            stream = self.adapter.decode_stream([latent, latent])
            first = next(stream)
            self.assertTrue(torch.is_grad_enabled())
            self.assertFalse(torch.is_inference_mode_enabled())
            stream.close()
            restarted = list(self.adapter.decode_stream([latent]))
            torch.testing.assert_close(restarted[0], first)
        self.assertEqual(len(instances), 2)


if __name__ == '__main__':
    unittest.main()
