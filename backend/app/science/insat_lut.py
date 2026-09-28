"""Strict count-to-temperature LUT decoding for future authorized INSAT files.

Adapted from the peer ConvectNow MOSDAC ingester's LUT branch. This utility
does not establish observation time, geolocation, registration, or data access.
"""

from pathlib import Path

import h5py
import numpy as np


def load_temperature_lut(
    path: Path,
    *,
    counts_key: str,
    lut_key: str,
) -> np.ndarray:
    """Decode a 2-D count field using an explicitly supplied Kelvin LUT.

    Missing calibration, invalid counts, and unknown units are errors. In
    particular, out-of-range counts are not silently clipped to a plausible
    thermal value.
    """
    with h5py.File(path, "r") as handle:
        if counts_key not in handle or lut_key not in handle:
            raise KeyError("Both the channel counts and its temperature LUT are required.")
        counts = np.asarray(handle[counts_key])
        lut_dataset = handle[lut_key]
        lut = np.asarray(lut_dataset)
        units = lut_dataset.attrs.get("units")

    if isinstance(units, bytes):
        units = units.decode("ascii")
    if units not in ("K", "Kelvin", "kelvin"):
        raise ValueError("Temperature LUT units must explicitly be Kelvin.")
    if counts.ndim != 2 or not np.issubdtype(counts.dtype, np.integer):
        raise ValueError("Channel counts must be a 2-D integer raster.")
    if lut.ndim != 1 or not np.issubdtype(lut.dtype, np.number) or len(lut) == 0:
        raise ValueError("Temperature LUT must be a nonempty numeric vector.")
    if not np.isfinite(lut).all() or np.any((lut <= 0) | (lut >= 500)):
        raise ValueError("Temperature LUT contains invalid Kelvin values.")
    if np.any(counts < 0) or np.any(counts >= len(lut)):
        raise ValueError("Channel counts fall outside the supplied temperature LUT.")

    return lut[counts].astype(np.float32)
