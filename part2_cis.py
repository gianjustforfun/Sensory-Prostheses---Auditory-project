"""run part 1's audio processing and generate the four cis pulse trains."""

import argparse
from pathlib import Path

import numpy as np

from src.audio import load_example_audio
from src.preprocessing import preprocess_audio
from src.filterbank import apply_filterbank
from src.envelope import extract_envelopes
from src.compression import compress_envelopes
from src.cis import encode_cis, plot_cis


def process_audio(example, offset=0):
    # use the same audio files and settings as part 1
    audio, fs = load_example_audio(example, sr=22050, duration=8, offset=offset)
    audio = preprocess_audio(audio)
    channels = apply_filterbank(audio, fs, [200, 500, 1250, 3150, 8000])
    envelopes = extract_envelopes(channels, fs, cutoff=400)
    return compress_envelopes(envelopes, alpha=1000), fs


def check_pulses(result, envelopes, fs):
    # only one channel should be active at a time
    assert np.all(np.count_nonzero(result.pulses, axis=0) <= 1)
    # check the time between pulses on each channel
    period = int(result.stimulation_fs / result.pulse_rate)
    assert np.all(np.diff(result.onset_samples, axis=1) == period)
    source_time = np.arange(len(envelopes[0])) / fs
    for channel, onsets in enumerate(result.onset_samples):
        # compare each pulse with the envelope value at its start
        expected = np.interp(onsets / result.stimulation_fs, source_time, envelopes[channel])
        assert np.allclose(result.amplitudes[channel], expected)
        offsets = np.arange(result.phase_samples)
        negative = result.pulses[channel, onsets[:, None] + offsets]
        positive = result.pulses[channel, onsets[:, None] + result.phase_samples + result.gap_samples + offsets]
        assert np.allclose(negative, -expected[:, None])
        assert np.allclose(positive, expected[:, None])
        # equal opposite phases should give zero net signed area
        assert np.allclose((negative + positive).sum(axis=1), 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, example, offset in [("speech", "libri1", 0), ("music", "brahms", 15)]:
        envelopes, fs = process_audio(example, offset)
        # use a separate clock so each 50 microsecond phase has five samples
        result = encode_cis(envelopes, fs, stimulation_fs=100000,
                            pulse_rate=1000, phase_duration_us=50,
                            interphase_gap_us=0)
        check_pulses(result, envelopes, fs)
        # save the pulse trains and timing information for part 3
        np.savez_compressed(
            args.output_dir / (name + "_cis.npz"), pulses=result.pulses,
            stimulation_fs=result.stimulation_fs, pulse_rate=result.pulse_rate,
            phase_samples=result.phase_samples, gap_samples=result.gap_samples,
            onset_samples=result.onset_samples, audio_fs=result.audio_fs,
            input_samples=result.input_samples,
        )
        if not args.no_plots:
            import matplotlib.pyplot as plt
            fig = plot_cis(result, start=0.5, duration=0.0033, title=name + " - cis pulse trains")
            fig.savefig(args.output_dir / (name + "_cis.png"))
            plt.close(fig)
        print(name, result.pulses.shape, "- all pulse checks passed")


if __name__ == "__main__":
    main()
