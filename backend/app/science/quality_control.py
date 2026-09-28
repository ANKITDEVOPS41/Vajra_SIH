from dataclasses import dataclass

import numpy as np
from scipy.ndimage import convolve, median_filter, uniform_filter


@dataclass(frozen=True)
class QualityControlResult:
    field: np.ndarray
    clutter_mask: np.ndarray
    anomalous_propagation_mask: np.ndarray
    raw_peak_dbz: float
    clean_peak_dbz: float

    @property
    def removed_pixel_count(self) -> int:
        return int(np.count_nonzero(self.clutter_mask | self.anomalous_propagation_mask))


class RadarQualityControl:
    """Deterministic reflectivity QC adapted from the supplied ConvectNow prototype.

    This module only identifies candidates. The masks and thresholds must be retained
    with every derived field so a reviewer can inspect what was removed.
    """

    def __init__(
        self,
        texture_threshold_db: float = 18.0,
        texture_window: int = 3,
        warm_cloud_threshold_k: float = 280.0,
        ap_reflectivity_threshold_dbz: float = 20.0,
        minimum_echo_dbz: float = 5.0,
        maximum_echo_dbz: float = 75.0,
    ) -> None:
        if texture_window < 3 or texture_window % 2 == 0:
            raise ValueError("texture_window must be an odd integer >= 3")
        self.texture_threshold_db = texture_threshold_db
        self.texture_window = texture_window
        self.warm_cloud_threshold_k = warm_cloud_threshold_k
        self.ap_reflectivity_threshold_dbz = ap_reflectivity_threshold_dbz
        self.minimum_echo_dbz = minimum_echo_dbz
        self.maximum_echo_dbz = maximum_echo_dbz

    def texture(self, reflectivity_dbz: np.ndarray) -> np.ndarray:
        field = self._clean_field(reflectivity_dbz)
        size = self.texture_window
        sample_count = float(size * size)

        neighbor_kernel = np.ones((size, size), dtype=np.float32)
        neighbor_kernel[size // 2, size // 2] = 0.0
        neighbor_kernel /= neighbor_kernel.sum()
        neighbor_mean = convolve(field, neighbor_kernel, mode="reflect")
        neighbor_square_mean = convolve(field**2, neighbor_kernel, mode="reflect")
        rms_difference = np.sqrt(
            np.maximum(0.0, field**2 - 2.0 * field * neighbor_mean + neighbor_square_mean)
        )

        local_mean = uniform_filter(field, size=size, mode="reflect")
        local_square_mean = uniform_filter(field**2, size=size, mode="reflect")
        variance = (sample_count / (sample_count - 1.0)) * np.maximum(
            0.0, local_square_mean - local_mean**2
        )
        return np.maximum(rms_difference, np.sqrt(variance))

    def filter_clutter(
        self,
        reflectivity_dbz: np.ndarray,
        *,
        replace_with_local_median: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        field = self._clean_field(reflectivity_dbz)
        mask = (self.texture(field) > self.texture_threshold_db) & (
            field > self.minimum_echo_dbz
        )
        filtered = field.copy()
        if replace_with_local_median:
            replacement = median_filter(field, size=self.texture_window, mode="reflect")
            filtered[mask] = replacement[mask]
        else:
            filtered[mask] = 0.0
        return filtered, mask

    def filter_anomalous_propagation(
        self,
        reflectivity_dbz: np.ndarray,
        satellite_brightness_temperature_k: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        field = self._clean_field(reflectivity_dbz)
        satellite = np.asarray(satellite_brightness_temperature_k, dtype=np.float32)
        if satellite.shape != field.shape:
            raise ValueError("radar and satellite grids must have the same shape")

        # Missing satellite pixels are unknown, not evidence of warm clear sky.
        mask = (
            np.isfinite(satellite)
            & (field >= self.ap_reflectivity_threshold_dbz)
            & (satellite >= self.warm_cloud_threshold_k)
        )
        filtered = field.copy()
        filtered[mask] = 0.0
        return filtered, mask

    def apply(
        self,
        reflectivity_dbz: np.ndarray,
        satellite_brightness_temperature_k: np.ndarray | None = None,
    ) -> QualityControlResult:
        raw = self._clean_field(reflectivity_dbz)
        filtered, clutter_mask = self.filter_clutter(raw)
        ap_mask = np.zeros_like(clutter_mask, dtype=bool)
        if satellite_brightness_temperature_k is not None:
            filtered, ap_mask = self.filter_anomalous_propagation(
                filtered, satellite_brightness_temperature_k
            )
        return QualityControlResult(
            field=filtered,
            clutter_mask=clutter_mask,
            anomalous_propagation_mask=ap_mask,
            raw_peak_dbz=float(raw.max(initial=0.0)),
            clean_peak_dbz=float(filtered.max(initial=0.0)),
        )

    def _clean_field(self, reflectivity_dbz: np.ndarray) -> np.ndarray:
        field = np.asarray(reflectivity_dbz, dtype=np.float32)
        if field.ndim != 2:
            raise ValueError("reflectivity field must be two-dimensional")
        return np.clip(
            np.nan_to_num(field, nan=0.0, posinf=self.maximum_echo_dbz, neginf=0.0),
            0.0,
            self.maximum_echo_dbz,
        )
