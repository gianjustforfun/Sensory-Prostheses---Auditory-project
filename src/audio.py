import librosa

def load_example_audio(example_name, sr=22050, duration=8.0, offset=0.0):
    """
    Load an example audio file provided by librosa.

    Parameters
    ----------
    example_name : str
        Name of the librosa example recording.
    sr : int
        Target sampling frequency in Hz.
    duration : float
        Duration of the loaded segment in seconds.
    offset : float
        Starting time of the segment in seconds.

    Returns
    -------
    audio : np.ndarray
        Mono audio signal.
    fs : int
        Sampling frequency.
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
    Load an external audio file.

    Parameters
    ----------
    filepath : str
        Path to the audio file.
    sr : int
        Target sampling frequency in Hz.
    duration : float or None
        Duration to load in seconds.
    offset : float
        Starting time in seconds.

    Returns
    -------
    audio : np.ndarray
        Mono audio signal.
    fs : int
        Sampling frequency.
    """

    audio, fs = librosa.load(
        filepath,
        sr=sr,
        mono=True,
        duration=duration,
        offset=offset
    )

    return audio, fs