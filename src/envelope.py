import numpy as np
from scipy.signal import butter, sosfiltfilt


def full_wave_rectify(signal):
    """
    Apply full-wave rectification to a signal.

    Parameters
    ----------
    signal : np.ndarray
        Input signal.

    Returns
    -------
    rectified_signal : np.ndarray
        Absolute value of the input signal.
    """

    return np.abs(signal)


def lowpass_filter(signal, fs, cutoff=400, order=4):
    """
    Apply a Butterworth low-pass filter.

    Parameters
    ----------
    signal : np.ndarray
        Input signal.
    fs : int
        Sampling frequency in Hz.
    cutoff : float
        Low-pass cutoff frequency in Hz.
    order : int
        Butterworth filter order.

    Returns
    -------
    filtered_signal : np.ndarray
        Low-pass filtered signal.
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
    Extract the temporal envelope of a band-pass filtered signal
    using full-wave rectification followed by low-pass filtering.
    """

    rectified_signal = full_wave_rectify(signal)

    envelope = lowpass_filter(
        rectified_signal,
        fs,
        cutoff=cutoff,
        order=order
    )

    # Numerical filtering can create very small negative values
    envelope = np.maximum(envelope, 0)

    return envelope


def extract_envelopes(channels, fs, cutoff=400, order=4):
    """
    Extract envelopes from multiple filter-bank channels.
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