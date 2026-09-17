"""Check pulse decoding, timing, silence, and repeatable acoustic synthesis."""

import unittest
from types import SimpleNamespace

import numpy as np

from src.cis import encode_cis
from src.compression import compress_envelopes, logarithmic_compression
from src.reconstruction import (
    extract_pulse_amplitudes,
    inverse_logarithmic_compression,
    interpolate_envelopes,
    noise_vocoder,
    reconstruct_audio,
)


class TestReconstruction(unittest.TestCase):
    def test_log_inverse(self):
        envelope = np.r_[0.0, np.geomspace(1e-12, 1.0, 200)]
        for alpha in (1.0, 1000.0):
            restored = inverse_logarithmic_compression(
                logarithmic_compression(envelope, alpha), alpha
            )
            np.testing.assert_allclose(restored, envelope, rtol=1e-12, atol=1e-14)

    def test_decoder_reads_pulses_without_cached_amplitudes(self):
        fs = 22050
        time = np.arange(2205) / fs
        compressed = np.array([0.3 + 0.2 * np.sin(2 * np.pi * f * time)
                               for f in (5, 11, 19, 31)])
        result = encode_cis(compressed, fs, interphase_gap_us=20,
                            channel_order=[3, 2, 1, 0])
        # The decoder must also work with no cached amplitude attribute.
        fields = vars(result).copy()
        fields.pop("amplitudes")
        pulses_only = SimpleNamespace(**fields)
        decoded = extract_pulse_amplitudes(pulses_only)
        expected = np.array([np.interp(starts / result.stimulation_fs,
                                       time, compressed[ch])
                             for ch, starts in enumerate(result.onset_samples)])
        np.testing.assert_allclose(decoded, expected, rtol=0, atol=1e-14)
        # Change one positive phase: only that decoded pulse must change.
        start = result.onset_samples[1, 2] + result.phase_samples + result.gap_samples
        result.pulses[1, start:start + result.phase_samples] = 0.125
        expected[1, 2] = 0.125
        np.testing.assert_allclose(extract_pulse_amplitudes(pulses_only), expected)

    def test_staggered_times_and_boundary_holds(self):
        onsets = np.array([[0, 100, 200], [25, 125, 225]])
        # Each row samples the same straight line at different times.
        sampled = 0.2 + 10 * onsets / 100000
        actual = interpolate_envelopes(sampled, onsets, 100000, 100000, 300)
        t = np.arange(300) / 100000
        for ch in range(2):
            expected = 0.2 + 10 * np.clip(t, onsets[ch, 0] / 100000,
                                         onsets[ch, -1] / 100000)
            np.testing.assert_allclose(actual[ch], expected, atol=1e-14)

    def test_silence_and_no_complete_frames(self):
        for length in (2205, 22):
            result = encode_cis(np.zeros((4, length)), 22050)
            decoded = reconstruct_audio(result, [200, 500, 1250, 3150, 8000])
            self.assertEqual(decoded["audio"].shape, (length,))
            self.assertTrue(np.all(decoded["audio"] == 0))
            self.assertTrue(np.all(decoded["envelopes"] == 0))
        # Nonzero envelopes shorter than a complete frame transmit no pulses.
        result = encode_cis(np.full((4, 22), 0.5), 22050)
        decoded = reconstruct_audio(result, [200, 500, 1250, 3150, 8000])
        self.assertTrue(np.all(decoded["audio"] == 0))

    def test_vocoder_seed_sum_and_relative_gains(self):
        envelopes = np.full((4, 2205), 0.2)
        edges = [200, 500, 1250, 3150, 8000]
        audio, channels = noise_vocoder(envelopes, 22050, edges)
        repeated, _ = noise_vocoder(envelopes, 22050, edges)
        changed_seed, _ = noise_vocoder(envelopes, 22050, edges, seed=43)
        self.assertTrue(np.all(np.isfinite(audio)))
        np.testing.assert_array_equal(audio, repeated)
        np.testing.assert_allclose(audio, channels.sum(axis=0))
        self.assertFalse(np.array_equal(audio, changed_seed))
        altered = envelopes.copy()
        altered[1] *= 0.25
        _, altered_channels = noise_vocoder(altered, 22050, edges)
        np.testing.assert_allclose(altered_channels[1], channels[1] * 0.25)
        np.testing.assert_allclose(altered_channels[[0, 2, 3]], channels[[0, 2, 3]])

    def test_wrapper_matches_separate_steps(self):
        envelopes = np.full((4, 2205), 0.2)
        result = encode_cis(compress_envelopes(envelopes), 22050)
        edges = [200, 500, 1250, 3150, 8000]
        sampled = inverse_logarithmic_compression(extract_pulse_amplitudes(result))
        interpolated = interpolate_envelopes(sampled, result.onset_samples,
                                             result.stimulation_fs, 22050, 2205)
        audio, _ = noise_vocoder(interpolated, 22050, edges)
        decoded = reconstruct_audio(result, edges)
        np.testing.assert_allclose(decoded["audio"], audio)
        np.testing.assert_allclose(decoded["envelopes"], 0.2, atol=1e-14)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            inverse_logarithmic_compression([0, 1], alpha=0)
        with self.assertRaises(ValueError):
            inverse_logarithmic_compression([1.1])
        with self.assertRaises(ValueError):
            noise_vocoder(np.ones((1, 100)), 16000, [200, 8000])
        with self.assertRaises(ValueError):
            interpolate_envelopes([[0.1, 0.2]], [[10, 5]], 100000, 22050, 100)


if __name__ == "__main__":
    unittest.main()
