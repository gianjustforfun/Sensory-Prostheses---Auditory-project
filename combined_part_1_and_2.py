"""parts 1 and 2 in one file: audio processing and cis pulse generation.

this is a standalone copy of the separate modules, with the same settings.
outputs use normalized amplitudes and must not be used to drive an implant.
"""

# src/audio.py
import librosa

def load_example_audio(example_name, sr=22050, duration=8.0, offset=0.0):
    """
    load an example audio file provided by librosa.

    parameters
    ----------
    example_name : str
        name of the librosa example recording.
    sr : int
        target sampling frequency in hz.
    duration : float
        duration of the loaded segment in seconds.
    offset : float
        starting time of the segment in seconds.

    returns
    -------
    audio : np.ndarray
        mono audio signal.
    fs : int
        sampling frequency.
    """

    path = librosa.ex(example_name)

    audio, fs = librosa.load(
        path,
        sr=sr,
        mono=True,
        duration=duration,
        offset=offset
    )

    return audio, fs


def load_audio_file(filepath, sr=22050, duration=None, offset=0.0):
    """
    load an external audio file.

    parameters
    ----------
    filepath : str
        path to the audio file.
    sr : int
        target sampling frequency in hz.
    duration : float or none
        duration to load in seconds.
    offset : float
        starting time in seconds.

    returns
    -------
    audio : np.ndarray
        mono audio signal.
    fs : int
        sampling frequency.
    """

    audio, fs = librosa.load(
        filepath,
        sr=sr,
        mono=True,
        duration=duration,
        offset=offset
    )

    return audio, fs


# src/preprocessing.py
import numpy as np


def preprocess_audio(audio):
    """
    apply basic preprocessing to a mono audio signal:
    1. remove dc offset
    2. peak-normalize the signal to [-1, 1]

    parameters
    ----------
    audio : np.ndarray
        input mono audio signal.

    returns
    -------
    processed_audio : np.ndarray
        preprocessed audio signal.
    """

    # remove dc offset
    processed_audio = audio - np.mean(audio)

    # peak normalization
    peak = np.max(np.abs(processed_audio))

    if peak > 0:
        processed_audio = processed_audio / peak

    return processed_audio


# src/filterbank.py
from scipy.signal import butter, sosfiltfilt


def bandpass_filter(audio, fs, lowcut, highcut, order=4):
    """
    apply a butterworth band-pass filter to an audio signal.
    """

    sos = butter(
        order,
        [lowcut, highcut],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    filtered_audio = sosfiltfilt(sos, audio)

    return filtered_audio

def apply_filterbank(audio, fs, band_edges, order=4):
    """
    split an audio signal into frequency channels.

    parameters
    ----------
    audio : np.ndarray
        input audio signal.
    fs : int
        sampling frequency.
    band_edges : list
        frequency boundaries in hz.
    order : int
        butterworth filter order.

    returns
    -------
    channels : list
        band-pass filtered signals.
    """

    channels = []

    for lowcut, highcut in zip(band_edges[:-1], band_edges[1:]):
        channel = bandpass_filter(
            audio,
            fs,
            lowcut,
            highcut,
            order
        )

        channels.append(channel)

    return channels


# src/envelope.py
import numpy as np
from scipy.signal import butter, sosfiltfilt


def full_wave_rectify(signal):
    """
    apply full-wave rectification to a signal.

    parameters
    ----------
    signal : np.ndarray
        input signal.

    returns
    -------
    rectified_signal : np.ndarray
        absolute value of the input signal.
    """

    return np.abs(signal)


def lowpass_filter(signal, fs, cutoff=400, order=4):
    """
    apply a butterworth low-pass filter.

    parameters
    ----------
    signal : np.ndarray
        input signal.
    fs : int
        sampling frequency in hz.
    cutoff : float
        low-pass cutoff frequency in hz.
    order : int
        butterworth filter order.

    returns
    -------
    filtered_signal : np.ndarray
        low-pass filtered signal.
    """

    sos = butter(
        order,
        cutoff,
        btype="lowpass",
        fs=fs,
        output="sos"
    )

    filtered_signal = sosfiltfilt(sos, signal)

    return filtered_signal


def extract_envelope(signal, fs, cutoff=400, order=4):
    """
    extract the temporal envelope of a band-pass filtered signal
    using full-wave rectification followed by low-pass filtering.
    """

    rectified_signal = full_wave_rectify(signal)

    envelope = lowpass_filter(
        rectified_signal,
        fs,
        cutoff=cutoff,
        order=order
    )

    # numerical filtering can create very small negative values
    envelope = np.maximum(envelope, 0)

    return envelope


def extract_envelopes(channels, fs, cutoff=400, order=4):
    """
    extract envelopes from multiple filter-bank channels.
    """

    envelopes = []

    for channel in channels:
        envelope = extract_envelope(
            channel,
            fs,
            cutoff=cutoff,
            order=order
        )

        envelopes.append(envelope)

    return envelopes


# src/compression.py
import numpy as np


def logarithmic_compression(envelope, alpha=1000.0):
    """
    apply logarithmic compression to a temporal envelope.

    parameters
    ----------
    envelope : np.ndarray
        input envelope with values between 0 and 1.
    alpha : float
        positive, dimensionless compression parameter.
        larger values produce stronger compression.

    returns
    -------
    compressed_envelope : np.ndarray
        compressed envelope with values between 0 and 1.
    """

    # reference:
    # lopez-poveda et al. (2025).
    # "binaural audio frontend processing for cochlear implants
    # inspired by the medial olivocochlear reflex."
    # frontiers in neuroscience, section 2.1.1, equation 1.
    # https://doi.org/10.3389/fnins.2025.1678288
    #
    # the study uses y = log(1 + c*x) / log(1 + c), with c = 1000
    # for its reference fs4 strategy. we adopt the same value as
    # alpha for our simplified cis model. this is a documented
    # parameter choice, not a universal standard for all cis systems.

    envelope = np.asarray(envelope, dtype=float)

    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and greater than zero.")

    if not np.all(np.isfinite(envelope)):
        raise ValueError("The envelope must contain only finite values.")

    if np.any(envelope < 0) or np.any(envelope > 1):
        raise ValueError("Envelope values must be between 0 and 1.")

    # apply compression without additional normalization or clipping.
    # np.log1p(z) accurately computes log(1 + z), including small z.
    compressed_envelope = (
        np.log1p(alpha * envelope) / np.log1p(alpha)
    )

    return compressed_envelope


def compress_envelopes(envelopes, alpha=1000.0):
    """
    apply logarithmic compression to multiple channel envelopes.

    parameters
    ----------
    envelopes : list
        temporal envelopes of the filter-bank channels.
    alpha : float
        positive compression parameter shared by all channels.

    returns
    -------
    compressed_envelopes : list
        compressed envelopes in the original channel order.
    """

    compressed_envelopes = []

    for envelope in envelopes:
        compressed_envelope = logarithmic_compression(
            envelope,
            alpha=alpha
        )

        compressed_envelopes.append(compressed_envelope)

    return compressed_envelopes


# src/cis.py
"""simulate balanced cis pulses with normalized amplitudes, not real currents."""

from dataclasses import dataclass
import numpy as np


@dataclass
class CISResult:
    pulses: np.ndarray  # (channels, stimulation samples), normalized amplitude
    stimulation_fs: int
    pulse_rate: float  # pulses/second/channel
    phase_samples: int
    gap_samples: int
    onset_samples: np.ndarray  # (channels, complete frames)
    amplitudes: np.ndarray  # envelope value held across both phases
    audio_fs: float
    input_samples: int


def encode_cis(envelopes, audio_fs, *, stimulation_fs=100000,
               pulse_rate=1000, phase_duration_us=50, interphase_gap_us=0,
               channel_order=None):
    """turn the compressed envelopes from part 1 into interleaved pulses.

    envelopes must have the same length and stay between 0 and 1.
    the default order is ch1, ch2, ch3, ch4 in each 1 ms frame.
    each pulse has a negative phase, an optional gap, and a positive phase.
    both phases use the envelope value sampled at the start of the pulse.
    only complete frames are used so the last pulse is not cut short.
    pulse timing must fit exactly on the stimulation sample grid.
    """
    # check the envelopes before building the pulse trains
    env = np.asarray(envelopes, dtype=float)
    if env.ndim != 2 or min(env.shape) == 0:
        raise ValueError("envelopes must have shape (channels, samples), nonempty")
    if not np.all(np.isfinite(env)) or np.any((env < 0) | (env > 1)):
        raise ValueError("compressed envelopes must be finite and in [0, 1]")
    for value in (audio_fs, stimulation_fs, pulse_rate, phase_duration_us):
        if not np.isfinite(value) or value <= 0:
            raise ValueError("sample rates, pulse rate and phase duration must be positive")
    if int(stimulation_fs) != stimulation_fs:
        raise ValueError("stimulation_fs must be an integer")
    if not np.isfinite(interphase_gap_us) or interphase_gap_us < 0:
        raise ValueError("interphase gap must be finite and nonnegative")
    if pulse_rate >= audio_fs / 2:
        raise ValueError("audio sampling rate must exceed twice the pulse rate")

    # timing needs whole samples so the two phases have equal lengths
    def grid_samples(value, name):
        rounded = round(value)
        if not np.isclose(value, rounded, rtol=0, atol=1e-8):
            raise ValueError(f"{name} is not exact on the stimulation sample grid")
        return rounded

    # convert the pulse period, phase length, and gap into samples
    stimulation_fs = int(stimulation_fs)
    frame = grid_samples(stimulation_fs / pulse_rate, "pulse period")
    phase = grid_samples(phase_duration_us * stimulation_fs / 1e6, "phase duration")
    gap = grid_samples(interphase_gap_us * stimulation_fs / 1e6, "interphase gap")
    if phase < 1:
        raise ValueError("phase duration must occupy at least one sample")
    channels, samples = env.shape
    order = list(range(channels)) if channel_order is None else list(channel_order)
    if any(not isinstance(ch, (int, np.integer)) for ch in order) or sorted(order) != list(range(channels)):
        raise ValueError("channel_order must be a permutation of zero-based channel indices")
    # give each channel an equal slot and check that its pulse fits
    slot = grid_samples(frame / channels, "channel slot")
    width = 2 * phase + gap
    if width > slot:
        raise ValueError("biphasic pulse plus gap does not fit in a channel slot")
    duration = samples / audio_fs
    output_samples = int(np.floor(duration * stimulation_fs + 1e-8))
    # leave any leftover time silent instead of cutting a pulse in half
    frames = output_samples // frame
    onsets = np.empty((channels, frames), dtype=np.int64)
    amplitudes = np.empty((channels, frames))
    pulses = np.zeros((channels, output_samples))
    source_time = np.arange(samples) / audio_fs
    for position, channel in enumerate(order):
        # shift each channel within the frame so the pulses do not overlap
        starts = np.arange(frames, dtype=np.int64) * frame + position * slot
        # get the envelope amplitude at each pulse start
        amp = np.interp(starts / stimulation_fs, source_time, env[channel])
        onsets[channel] = starts
        amplitudes[channel] = amp
        # keep the same amplitude for both phases so their signed areas cancel
        for offset in range(phase):
            pulses[channel, starts + offset] = -amp
            pulses[channel, starts + phase + gap + offset] = amp
    return CISResult(pulses, stimulation_fs, float(pulse_rate), phase, gap,
                     onsets, amplitudes, float(audio_fs), samples)


def plot_cis(result, *, start=0, duration=0.0033, title="CIS pulse trains"):
    """plot a short section of the pulse trains, one channel per axis."""
    import matplotlib.pyplot as plt
    if start < 0 or duration <= 0:
        raise ValueError("start must be nonnegative and duration positive")
    first = int(start * result.stimulation_fs)
    last = min(result.pulses.shape[1], int((start + duration) * result.stimulation_fs))
    if first >= last:
        raise ValueError("plot window does not intersect the output")
    # use milliseconds to make the short pulses easier to see
    time_ms = np.arange(first, last) / result.stimulation_fs * 1000
    fig, axes = plt.subplots(result.pulses.shape[0], 1, sharex=True,
                             figsize=(12, 7), squeeze=False)
    for channel, ax in enumerate(axes[:, 0]):
        ax.step(time_ms, result.pulses[channel, first:last], where="post")
        ax.set_ylabel(f"CH{channel + 1}")
        ax.set_ylim(-1.05, 1.05)
        ax.grid(alpha=0.3)
    axes[-1, 0].set_xlabel("Time [ms]")
    fig.suptitle(title + " — normalized amplitude")
    fig.tight_layout()
    return fig


# part2_cis.py
"""run part 1's audio processing and generate the four cis pulse trains."""

import argparse
from pathlib import Path

import numpy as np



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
