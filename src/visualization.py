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


def plot_filterbank_waveforms(channels, fs, band_edges, title="Filter Bank Outputs"):
    """
    Plot the time-domain waveforms of the filter-bank channels.
    """

    time = np.arange(len(channels[0])) / fs

    fig, axes = plt.subplots(
        len(channels),
        1,
        figsize=(12, 8),
        sharex=True
    )

    for i, channel in enumerate(channels):
        axes[i].plot(time, channel)

        axes[i].set_ylabel("Amplitude")
        axes[i].set_title(
            f"CH{i+1}: {band_edges[i]}-{band_edges[i+1]} Hz"
        )

        axes[i].grid(True)

    axes[-1].set_xlabel("Time [s]")

    fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def plot_filterbank_psd(channels, fs, band_edges, title="Filter Bank PSD"):
    """
    Plot the power spectral density of each filter-bank channel.
    """

    fig, axes = plt.subplots(
        len(channels),
        1,
        figsize=(12, 8),
        sharex=True
    )

    for i, channel in enumerate(channels):
        frequencies, psd = welch(
            channel,
            fs=fs,
            nperseg=2048
        )

        axes[i].semilogy(frequencies, psd)

        axes[i].axvline(
            band_edges[i],
            linestyle="--"
        )

        axes[i].axvline(
            band_edges[i + 1],
            linestyle="--"
        )

        axes[i].set_ylabel("PSD")

        axes[i].set_title(
            f"CH{i + 1}: {band_edges[i]}-{band_edges[i + 1]} Hz"
        )

        axes[i].grid(True)

    axes[-1].set_xlabel("Frequency [Hz]")
    axes[-1].set_xlim(0, 9000)

    fig.suptitle(title)
    plt.tight_layout()
    plt.show()