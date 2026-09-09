"""Optional fixed-shape chromatic timing terms, normalized at 1400 MHz.

Miles et al. (arXiv:2412.01148), equations 8, 10 and 11. Gaussian amplitudes
are fitted linearly; annual amplitude and phase are fitted with two columns.
Shape parameters and scattering hyperparameters remain fixed, not inferred.
"""

import numpy as np


def frequency_scale(radio_mhz, index):
    radio = np.asarray(radio_mhz, dtype=float)
    if radio.ndim != 1 or not np.all(np.isfinite(radio)) or np.any(radio <= 0):
        raise ValueError("Radio frequencies must be a finite positive MHz vector")
    if not np.isfinite(index) or index < 0:
        raise ValueError("Chromatic index must be finite and nonnegative")
    scale = (1400.0 / radio) ** index
    if not np.all(np.isfinite(scale)):
        raise ValueError("Chromatic frequency scaling overflowed")
    return scale


def scattering_covariance(temporal_covariance, radio_mhz, index):
    """Apply frequency scaling to BOTH ends of the covariance, in seconds squared."""
    scale = frequency_scale(radio_mhz, index)
    covariance = np.asarray(temporal_covariance, dtype=float)
    if covariance.shape != (len(scale), len(scale)) or not np.all(np.isfinite(covariance)):
        raise ValueError("Temporal covariance must match the radio-frequency vector")
    return covariance * scale[:, None] * scale[None, :]


def event_design(times_mjd, radio_mhz, event):
    """Dimensionless columns; their fitted coefficients have units of seconds.

    Use a decaying Gaussian. The positive exponent printed in Miles v1 eq. 10
    is inconsistent with a localized Gaussian event. Annual sine/cosine span
    is independent of the arbitrary phase origin, chosen as the first TOA.
    """
    times = np.asarray(times_mjd, dtype=float)
    scale = frequency_scale(radio_mhz, event["index"])
    if times.shape != scale.shape or not np.all(np.isfinite(times)):
        raise ValueError("Event times must be a finite MJD vector matching frequencies")
    if event["kind"] == "gaussian":
        center, width = event["center_mjd"], event["width_days"]
        if not np.isfinite(center) or not np.isfinite(width) or width <= 0:
            raise ValueError("Gaussian center and positive width must be finite, in days")
        return (np.exp(-0.5 * ((times - center) / width) ** 2) * scale)[:, None]
    if event["kind"] == "annual":
        phase = 2 * np.pi * (times - times.min()) / 365.25
        return np.column_stack([np.sin(phase) * scale, np.cos(phase) * scale])
    raise ValueError("Unsupported chromatic event kind")
