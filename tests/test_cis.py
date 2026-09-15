import unittest
import numpy as np
from src.cis import encode_cis


class TestCIS(unittest.TestCase):
    def setUp(self):
        self.env = np.full((4, 2205), 0.7)

    def test_timing_balance_and_nonoverlap(self):
        result = encode_cis(self.env, 22050)
        self.assertEqual(result.pulses.shape, (4, 10000))
        self.assertEqual(result.onset_samples.shape, (4, 100))
        np.testing.assert_array_equal(np.diff(result.onset_samples), 100)
        np.testing.assert_array_equal(result.onset_samples[:, 0], [0, 25, 50, 75])
        self.assertTrue(np.all(np.count_nonzero(result.pulses, axis=0) <= 1))
        np.testing.assert_allclose(result.pulses.sum(axis=1), 0, atol=1e-12)
        for channel, starts in enumerate(result.onset_samples):
            for onset in starts:
                np.testing.assert_allclose(result.pulses[channel, onset:onset+5], -0.7)
                np.testing.assert_allclose(result.pulses[channel, onset+5:onset+10], 0.7)

    def test_interpolation(self):
        env = np.tile(np.arange(2205) / 2205, (4, 1))
        result = encode_cis(env, 22050)
        np.testing.assert_allclose(result.amplitudes, result.onset_samples / 10000)

    def test_order_and_gap(self):
        result = encode_cis(self.env, 22050, channel_order=[3, 2, 1, 0], interphase_gap_us=20)
        np.testing.assert_array_equal(result.onset_samples[:, 0], [75, 50, 25, 0])
        np.testing.assert_array_equal(result.pulses[3, 5:7], 0)
        np.testing.assert_allclose(result.pulses[3, 7:12], 0.7)

    def test_silence_and_short_input(self):
        result = encode_cis(np.zeros((4, 22)), 22050)
        self.assertEqual(result.onset_samples.shape, (4, 0))
        self.assertFalse(np.any(result.pulses))

    def test_reject_invalid_inputs(self):
        for env in ([], [[-1]], [[np.nan]], [[1.1]], [[[0]]]):
            with self.assertRaises(ValueError):
                encode_cis(env, 22050)
        for kwargs in ({"phase_duration_us": 130}, {"phase_duration_us": 55},
                       {"pulse_rate": 1100}, {"channel_order": [0, 0, 1, 2]},
                       {"interphase_gap_us": -1}, {"audio_fs": 0}):
            params = {"audio_fs": 22050, **kwargs}
            with self.assertRaises(ValueError):
                encode_cis(self.env, **params)

    def test_part1_pipeline_connection(self):
        from src.filterbank import apply_filterbank
        from src.envelope import extract_envelopes
        from src.compression import compress_envelopes
        fs = 22050
        time = np.arange(fs) / fs
        # use four tones to test the connection to part 1 without downloading audio
        audio = sum(0.1 * np.sin(2 * np.pi * freq * time)
                    for freq in (350, 850, 2200, 5000))
        channels = apply_filterbank(audio, fs, [200, 500, 1250, 3150, 8000])
        envelopes = compress_envelopes(extract_envelopes(channels, fs))
        result = encode_cis(envelopes, fs)
        self.assertEqual(result.onset_samples.shape, (4, 1000))
        self.assertTrue(np.all(np.count_nonzero(result.pulses, axis=0) <= 1))
        np.testing.assert_allclose(result.pulses.sum(axis=1), 0, atol=1e-10)

    def test_combined_encoder_matches_separate_file(self):
        from combined_cis import encode_cis as combined_encode
        separate = encode_cis(self.env, 22050)
        combined = combined_encode(self.env, 22050)
        np.testing.assert_array_equal(separate.pulses, combined.pulses)
        np.testing.assert_array_equal(separate.onset_samples, combined.onset_samples)


if __name__ == "__main__":
    unittest.main()
