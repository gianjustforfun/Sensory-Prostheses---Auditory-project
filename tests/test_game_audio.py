"""Check the game band layout, shared playback gain policy, and six-level path."""

import unittest

import numpy as np

from prepare_game_audio import (
    BASE_EDGES, CHANNEL_COUNTS, PEAK_LIMIT, make_band_edges,
    match_playback_levels, synthesize_level,
)


class TestGameAudio(unittest.TestCase):
    def test_bands_preserve_original_boundaries_and_are_nested(self):
        np.testing.assert_array_equal(make_band_edges(4), BASE_EDGES)
        previous = None
        for count in CHANNEL_COUNTS:
            edges = make_band_edges(count)
            self.assertEqual(len(edges), count + 1)
            self.assertEqual(edges[0], 200)
            self.assertEqual(edges[-1], 8000)
            self.assertTrue(np.all(np.diff(edges) > 0))
            if previous is not None:
                for boundary in previous:
                    self.assertTrue(np.any(np.isclose(edges, boundary)))
            previous = edges

    def test_one_global_gain_per_signal_and_shared_rms_after_peak_limit(self):
        # A sparse waveform needs attenuation after matching RMS.
        sparse = np.zeros(2000)
        sparse[500] = 1
        signals = {"sparse": sparse, "tone": np.sin(np.arange(2000) * 0.15)}
        matched, gains, common = match_playback_levels(signals)
        self.assertLess(common, 1)
        rms = []
        for name, signal in matched.items():
            np.testing.assert_allclose(signal, signals[name] * gains[name])
            self.assertLessEqual(np.max(np.abs(signal)), PEAK_LIMIT + 1e-12)
            rms.append(np.sqrt(np.mean(signal ** 2)))
        np.testing.assert_allclose(rms[0], rms[1], rtol=1e-12)
        with self.assertRaises(ValueError):
            match_playback_levels({"silence": np.zeros(100)})

    def test_all_six_levels_encode_and_decode_actual_pulses(self):
        fs = 22050
        time = np.arange(2205) / fs
        audio = 0.2 * np.sin(2 * np.pi * 350 * time)
        audio += 0.1 * np.sin(2 * np.pi * 2100 * time)
        outputs = []
        for count in CHANNEL_COUNTS:
            output, info = synthesize_level(audio, fs, count)
            self.assertEqual(output.shape, audio.shape)
            self.assertTrue(np.all(np.isfinite(output)))
            self.assertGreater(np.max(np.abs(output)), 0)
            self.assertEqual(info["phase_samples"], 4)
            self.assertLessEqual(2 * info["phase_samples"], info["slot_samples"])
            self.assertLessEqual(info["pulse_decoding_max_error"], 1e-12)
            outputs.append(output)
        for lower, higher in zip(outputs[:-1], outputs[1:]):
            self.assertFalse(np.array_equal(lower, higher))


if __name__ == "__main__":
    unittest.main()
