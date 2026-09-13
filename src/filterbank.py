from scipy.signal import butter, sosfiltfilt


def bandpass_filter(audio, fs, lowcut, highcut, order=4):
    """
    Apply a Butterworth band-pass filter to an audio signal.
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
    Split an audio signal into frequency channels.

    Parameters
    ----------
    audio : np.ndarray
        Input audio signal.
    fs : int
        Sampling frequency.
    band_edges : list
        Frequency boundaries in Hz.
    order : int
        Butterworth filter order.

    Returns
    -------
    channels : list
        Band-pass filtered signals.
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