"""Timing controls must detect real offsets without wrapping or retiming the media."""
import unittest

import numpy as np

from scripts.review_lip_sync import displayed_indices, offset_score, shift_audio


class LipSyncReviewTests(unittest.TestCase):
    def test_resampling_preserves_mux_gap_and_twenty_fps_speed(self):
        timestamps = [0, .09267578125, .14267578125, .19267578125, .24267578125]
        self.assertEqual(displayed_indices(timestamps, 7).tolist(), [0, 0, 0, 1, 2, 3, 3])
        self.assertEqual(displayed_indices([0,.05,.1,.15,.2], 5).tolist(), [0,0,1,2,3])

    def test_audio_shift_preserves_duration_and_never_wraps(self):
        data = np.arange(1, 7)
        self.assertEqual(shift_audio(data, 2).tolist(), [0,0,1,2,3,4])
        self.assertEqual(shift_audio(data, -2).tolist(), [3,4,5,6,0,0])
        self.assertEqual(shift_audio(data, 0).tolist(), data.tolist())
        self.assertEqual(data.tolist(), list(range(1,7)))

    def test_known_offsets_and_flat_negative_control(self):
        # Distinct random feature windows stand in for neural embeddings. This
        # tests the scorer's sign/edges independently of any downloaded weights.
        lips = np.random.default_rng(7).normal(size=(100, 12))
        for shift in [-10,-5,0,5,10]:
            audio = np.stack([shift_audio(lips[:, channel], shift) for channel in range(12)], axis=1)
            result = offset_score(lips, audio, radius=15)
            self.assertEqual(result['audio_delay_ms'], shift*40)
            self.assertAlmostEqual(result['distance'], 0)
            self.assertFalse(result['at_search_boundary'])
        flat = offset_score(np.zeros((100,12)), np.zeros((100,12)))
        self.assertEqual(flat['confidence'], 0)
        self.assertTrue(flat['at_search_boundary'])

    def test_invalid_or_short_input_cannot_be_accepted(self):
        for timestamps in [[0,0,.1], [0,float('nan'),.1], [.1,.2], [0,.1,.05]]:
            with self.assertRaises(ValueError):
                displayed_indices(timestamps, 5)
        with self.assertRaises(ValueError):
            displayed_indices([0,.05,.1], 20)
        for value in [np.zeros((49,12)), np.full((100,12), np.nan)]:
            with self.assertRaises(ValueError):
                offset_score(value, value)
        with self.assertRaises(ValueError):
            shift_audio(np.ones(10), 10)


if __name__ == '__main__':
    unittest.main()
