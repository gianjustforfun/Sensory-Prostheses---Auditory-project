import numpy as np
import matplotlib.pyplot as plt


def plot_frequency_spectrum(audio, fs, title="Frequency Spectrum", max_freq=None):
    """
    Plot the single-sided magnitude spectrum of an audio signal.

    Parameters
    ----------
    audio : np.ndarray
        Input audio signal.
    fs : int
        Sampling frequency in Hz.
    title : str
        Plot title.
    max_freq : float or None
        Maximum frequency displayed in Hz.
    """

    n = len(audio)

    spectrum = np.fft.rfft(audio)
    frequencies = np.fft.rfftfreq(n, d=1/fs)

    magnitude = np.abs(spectrum) / n

    plt.figure(figsize=(12, 4))
    plt.plot(frequencies, magnitude)

    if max_freq is not None:
        plt.xlim(0, max_freq)

    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Magnitude")
    plt.title(title)
    plt.grid(True)
    plt.show()



from scipy.signal import welch

def plot_psd(audio, fs, title="Power Spectral Density", max_freq=10000):
    """
    Plot the power spectral density using Welch's method.
    """

    frequencies, psd = welch(
        audio,
        fs=fs,
        nperseg=2048
    )

    plt.figure(figsize=(12, 4))
    plt.semilogy(frequencies, psd)

    plt.xlim(0, max_freq)

    plt.xlabel("Frequency [Hz]")
    plt.ylabel("PSD")
    plt.title(title)
    plt.grid(True)
    plt.show()


from scipy.signal import welch
import numpy as np

def compute_band_power(audio, fs, band_edges, nperseg=2048):
    frequencies, psd = welch(
        audio,
        fs=fs,
        nperseg=nperseg
    )

    band_powers = []

    for low, high in zip(band_edges[:-1], band_edges[1:]):
        mask = (frequencies >= low) & (frequencies < high)

        power = np.trapezoid(
            psd[mask],
            frequencies[mask]
        )

        band_powers.append(power)

    total_power = sum(band_powers)

    relative_power = [
        100 * power / total_power
        for power in band_powers
    ]

    return relative_power