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
