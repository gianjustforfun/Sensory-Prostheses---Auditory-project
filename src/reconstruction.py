"""Recover envelopes from CIS pulses and synthesize an acoustic illustration."""

import numpy as np

from .filterbank import bandpass_filter


def extract_pulse_amplitudes(result):
    """
    Read the compressed envelope samples from the positive pulse phases.

    Parameters
    ----------
    result : CISResult
        Output of src.cis.encode_cis. Pulse amplitudes are normalized,
        dimensionless values. The stored result.amplitudes is never used.

    Returns
    -------
    amplitudes : np.ndarray
        Shape (channels, complete frames), including zero-amplitude pulses.

    Notes
    -----
    The encoder uses negative phase, optional gap, then positive phase.
    Metadata identifies even silent pulses. Averaging both signed phases
    together would cancel the information because each pulse is balanced.
    """
    pulses = np.asarray(result.pulses, dtype=float)
    onsets = np.asarray(result.onset_samples)
    phase = result.phase_samples
    gap = result.gap_samples

    if pulses.ndim != 2 or pulses.shape[0] == 0:
        raise ValueError("pulses must have shape (channels, stimulation samples).")
    if onsets.ndim != 2 or onsets.shape[0] != pulses.shape[0]:
        raise ValueError("onset_samples must have one row per pulse channel.")
    if not np.issubdtype(onsets.dtype, np.integer):
        raise ValueError("Pulse onset indices must be integers.")
    if not isinstance(phase, (int, np.integer)) or phase < 1:
        raise ValueError("phase_samples must be a positive integer.")
    if not isinstance(gap, (int, np.integer)) or gap < 0:
        raise ValueError("gap_samples must be a nonnegative integer.")
    if np.any(onsets < 0) or np.any(onsets + 2 * phase + gap > pulses.shape[1]):
        raise ValueError("Each complete pulse must fit inside the pulse array.")
    if np.any(np.diff(onsets, axis=1) <= 0):
        raise ValueError("Pulse onsets must increase within each channel.")

    amplitudes = np.empty(onsets.shape, dtype=float)
    offsets = np.arange(phase)

    for channel in range(pulses.shape[0]):
        indices = onsets[channel, :, None] + phase + gap + offsets
        positive_phase = pulses[channel, indices]
        if not np.all(np.isfinite(positive_phase)):
            raise ValueError("Positive pulse phases must contain finite values.")
        if np.any((positive_phase < 0) | (positive_phase > 1)):
            raise ValueError("Expected normalized positive pulse phases in [0, 1].")
        amplitudes[channel] = positive_phase.mean(axis=1)

    return amplitudes


def inverse_logarithmic_compression(compressed_envelopes, alpha=1000.0):
    """
    Undo the mapping in src.compression using the same positive alpha.

    Input and output have the same shape and contain values in [0, 1].
    This is an acoustic-decoder modeling choice, not a biological model
    of how an implanted listener perceives electrical stimulation.
    """
    compressed_envelopes = np.asarray(compressed_envelopes, dtype=float)
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and greater than zero.")
    if not np.all(np.isfinite(compressed_envelopes)):
        raise ValueError("Compressed envelopes must contain finite values.")
    if np.any((compressed_envelopes < 0) | (compressed_envelopes > 1)):
        raise ValueError("Compressed envelopes must be between 0 and 1.")

    # Algebraic inverse of c = log(1 + alpha * e) / log(1 + alpha).
    # alpha must match the encoder. The existing compression.py documents
    # alpha = 1000 using Lopez-Poveda et al. (2025), Section 2.1.1, Eq. 1:
    # https://doi.org/10.3389/fnins.2025.1678288
    # That paper's reference FS4 value is a project choice, not a universal
    # CIS constant. No additional per-channel normalization is applied.
    return np.expm1(compressed_envelopes * np.log1p(alpha)) / alpha


def interpolate_envelopes(sampled_envelopes, onset_samples,
                          stimulation_fs, audio_fs, input_samples):
    """
    Interpolate the recovered samples onto the original audio time grid.

    sampled_envelopes and onset_samples have shape (channels, frames).
    The returned array has shape (channels, input_samples). Each channel
    uses its own staggered onset times, not a common frame-start clock.

    Before the first and after the last pulse, hold the nearest sample.
    This also fills the incomplete final frame omitted by encode_cis.
    If there are no complete frames, return zero envelopes: no envelope
    information was transmitted. Linear interpolation is approximate.
    """
    sampled = np.asarray(sampled_envelopes, dtype=float)
    onsets = np.asarray(onset_samples)
    if sampled.ndim != 2 or sampled.shape[0] == 0 or sampled.shape != onsets.shape:
        raise ValueError("Samples and onsets must share shape (channels, frames).")
    if not np.all(np.isfinite(sampled)) or np.any(sampled < 0):
        raise ValueError("Envelope samples must be finite and nonnegative.")
    if not np.issubdtype(onsets.dtype, np.integer) or np.any(onsets < 0):
        raise ValueError("Pulse onset indices must be nonnegative integers.")
    if np.any(np.diff(onsets, axis=1) <= 0):
        raise ValueError("Pulse onsets must increase within each channel.")
    for fs in (stimulation_fs, audio_fs):
        if not np.isfinite(fs) or fs <= 0:
            raise ValueError("Sampling frequencies must be finite and positive.")
    if not isinstance(input_samples, (int, np.integer)) or input_samples < 1:
        raise ValueError("input_samples must be a positive integer.")

    envelopes = np.zeros((sampled.shape[0], input_samples))
    if sampled.shape[1] == 0:
        return envelopes

    audio_time = np.arange(input_samples) / audio_fs
    pulse_times = onsets / stimulation_fs
    if np.any(pulse_times >= input_samples / audio_fs):
        raise ValueError("Pulse onsets must lie within the input duration.")

    for channel in range(sampled.shape[0]):
        envelopes[channel] = np.interp(
            audio_time,
            pulse_times[channel],
            sampled[channel],
            left=sampled[channel, 0],
            right=sampled[channel, -1]
        )

    return envelopes


def noise_vocoder(envelopes, fs, band_edges, order=4, seed=42):
    """
    Modulate band-limited noise with the recovered temporal envelopes.

    Parameters
    ----------
    envelopes : np.ndarray
        Nonnegative array with shape (channels, audio samples).
    fs : float
        Audio sampling frequency in Hz.
    band_edges : sequence
        Same increasing frequency boundaries and channel order as part 1.
    order : int
        Butterworth filter order, as in src.filterbank.bandpass_filter.
    seed : int
        Fixed random seed for repeatable noise carriers.

    Returns
    -------
    audio : np.ndarray
        Sum of the synthesized channels, without output normalization.
    channels : np.ndarray
        Individual synthesized channels, shape matching envelopes.

    Notes
    -----
    Carriers are RMS-normalized BEFORE modulation so random noise energy
    and bandwidth do not introduce an arbitrary gain across channels.
    Modulated channels are filtered again to limit modulation sidebands.
    Channel outputs are not normalized separately. The final waveform
    may exceed [-1, 1]; apply one global gain before playback or WAV export.
    Forward/backward filtering is offline and noncausal.
    """
    envelopes = np.asarray(envelopes, dtype=float)
    edges = np.asarray(band_edges, dtype=float)
    if envelopes.ndim != 2 or min(envelopes.shape) == 0:
        raise ValueError("envelopes must have shape (channels, samples), nonempty.")
    if not np.all(np.isfinite(envelopes)) or np.any(envelopes < 0):
        raise ValueError("Envelopes must be finite and nonnegative.")
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs must be finite and positive.")
    if edges.ndim != 1 or len(edges) != envelopes.shape[0] + 1:
        raise ValueError("Provide one more band edge than envelope channels.")
    if (not np.all(np.isfinite(edges)) or np.any(np.diff(edges) <= 0)
            or edges[0] <= 0 or edges[-1] >= fs / 2):
        raise ValueError("Band edges must increase strictly between 0 and Nyquist.")
    if not isinstance(order, (int, np.integer)) or order < 1:
        raise ValueError("Filter order must be a positive integer.")

    channels = np.zeros_like(envelopes)
    if not np.any(envelopes):
        return channels.sum(axis=0), channels
    # A Butterworth band-pass of this order has 'order' SOS sections.
    if envelopes.shape[1] <= 3 * (2 * order + 1):
        raise ValueError("Audio is too short for forward/backward band-pass filtering.")

    # Noise-envelope synthesis follows the general approach in:
    # Shannon et al. (1995), "Speech Recognition with Primarily Temporal
    # Cues", Science 270, 303-304. DOI: 10.1126/science.270.5234.303.
    # Our filters and pulse-decoding steps are project-specific choices.
    rng = np.random.default_rng(seed)
    for channel, (lowcut, highcut) in enumerate(zip(edges[:-1], edges[1:])):
        noise = rng.standard_normal(envelopes.shape[1])
        carrier = bandpass_filter(noise, fs, lowcut, highcut, order=order)
        carrier_rms = np.sqrt(np.mean(carrier ** 2))
        if not np.isfinite(carrier_rms) or carrier_rms == 0:
            raise ValueError("Could not generate a finite, nonzero noise carrier.")
        carrier = carrier / carrier_rms
        modulated = envelopes[channel] * carrier
        channels[channel] = bandpass_filter(
            modulated, fs, lowcut, highcut, order=order
        )

    return channels.sum(axis=0), channels


def reconstruct_audio(result, band_edges, alpha=1000.0, order=4, seed=42):
    """
    Run all decoding steps using only CIS pulses and known parameters.

    Returns a dictionary containing raw audio, synthesized channels,
    sampled compressed amplitudes, sampled uncompressed envelopes, and
    audio-rate envelopes. No original audio or original envelopes enter
    this function. result.amplitudes is not read.
    """
    compressed = extract_pulse_amplitudes(result)
    sampled = inverse_logarithmic_compression(compressed, alpha=alpha)
    envelopes = interpolate_envelopes(
        sampled, result.onset_samples, result.stimulation_fs,
        result.audio_fs, result.input_samples
    )
    audio, channels = noise_vocoder(
        envelopes, result.audio_fs, band_edges, order=order, seed=seed
    )

    return {
        "audio": audio,
        "channels": channels,
        "sampled_compressed": compressed,
        "sampled_envelopes": sampled,
        "envelopes": envelopes
    }
