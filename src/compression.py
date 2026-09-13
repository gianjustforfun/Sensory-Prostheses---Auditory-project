import numpy as np


def logarithmic_compression(envelope, alpha=1000.0):
    """
    Apply logarithmic compression to a temporal envelope.

    Parameters
    ----------
    envelope : np.ndarray
        Input envelope with values between 0 and 1.
    alpha : float
        Positive, dimensionless compression parameter.
        Larger values produce stronger compression.

    Returns
    -------
    compressed_envelope : np.ndarray
        Compressed envelope with values between 0 and 1.
    """

    # Reference:
    # Lopez-Poveda et al. (2025).
    # "Binaural audio frontend processing for cochlear implants
    # inspired by the medial olivocochlear reflex."
    # Frontiers in Neuroscience, Section 2.1.1, Equation 1.
    # https://doi.org/10.3389/fnins.2025.1678288
    #
    # The study uses y = log(1 + c*x) / log(1 + c), with c = 1000
    # for its reference FS4 strategy. We adopt the same value as
    # alpha for our simplified CIS model. This is a documented
    # parameter choice, not a universal standard for all CIS systems.

    envelope = np.asarray(envelope, dtype=float)

    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and greater than zero.")

    if not np.all(np.isfinite(envelope)):
        raise ValueError("The envelope must contain only finite values.")

    if np.any(envelope < 0) or np.any(envelope > 1):
        raise ValueError("Envelope values must be between 0 and 1.")

    # Apply compression without additional normalization or clipping.
    # np.log1p(z) accurately computes log(1 + z), including small z.
    compressed_envelope = (
        np.log1p(alpha * envelope) / np.log1p(alpha)
    )

    return compressed_envelope


def compress_envelopes(envelopes, alpha=1000.0):
    """
    Apply logarithmic compression to multiple channel envelopes.

    Parameters
    ----------
    envelopes : list
        Temporal envelopes of the filter-bank channels.
    alpha : float
        Positive compression parameter shared by all channels.

    Returns
    -------
    compressed_envelopes : list
        Compressed envelopes in the original channel order.
    """

    compressed_envelopes = []

    for envelope in envelopes:
        compressed_envelope = logarithmic_compression(
            envelope,
            alpha=alpha
        )

        compressed_envelopes.append(compressed_envelope)

    return compressed_envelopes