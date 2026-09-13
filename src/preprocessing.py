import numpy as np


def preprocess_audio(audio):
    """
    Apply basic preprocessing to a mono audio signal:
    1. Remove DC offset
    2. Peak-normalize the signal to [-1, 1]

    Parameters
    ----------
    audio : np.ndarray
        Input mono audio signal.

    Returns
    -------
    processed_audio : np.ndarray
        Preprocessed audio signal.
    """

    # Remove DC offset
    processed_audio = audio - np.mean(audio)

    # Peak normalization
    peak = np.max(np.abs(processed_audio))

    if peak > 0:
        processed_audio = processed_audio / peak

    return processed_audio