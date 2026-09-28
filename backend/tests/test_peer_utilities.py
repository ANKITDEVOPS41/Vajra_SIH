"""Isolated peer-derived science utilities; no live-source or location claims."""

import h5py
import numpy as np
import pytest

from backend.app.science.insat_lut import load_temperature_lut
from backend.app.science.verification import ContingencyTable, equitable_threat_score


def test_insat_temperature_lut_decodes_only_supplied_calibration(tmp_path):
    path = tmp_path / "thermal.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("IMG_TIR1", data=np.array([[0, 1], [2, 1]], dtype=np.uint16))
        handle.create_dataset("IMG_TIR1_TEMP", data=np.array([210.0, 240.5, 295.0])).attrs["units"] = "K"

    kelvin = load_temperature_lut(path, counts_key="IMG_TIR1", lut_key="IMG_TIR1_TEMP")
    np.testing.assert_allclose(kelvin, [[210.0, 240.5], [295.0, 240.5]])
    assert kelvin.dtype == np.float32


@pytest.mark.parametrize("counts,lut", [
    ([0, 3], [210.0, 240.0]),
    ([0, -1], [210.0, 240.0]),
    ([0, 1], [210.0, np.nan]),
])
def test_insat_lut_refuses_invalid_calibration_or_counts(tmp_path, counts, lut):
    path = tmp_path / "bad.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("IMG_TIR1", data=np.array([counts], dtype=np.int16))
        handle.create_dataset("IMG_TIR1_TEMP", data=np.array(lut)).attrs["units"] = "K"
    with pytest.raises(ValueError):
        load_temperature_lut(path, counts_key="IMG_TIR1", lut_key="IMG_TIR1_TEMP")


def test_insat_lut_does_not_synthesize_missing_calibration(tmp_path):
    path = tmp_path / "no-lut.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("IMG_TIR1", data=np.array([[1]], dtype=np.uint16))
    with pytest.raises(KeyError):
        load_temperature_lut(path, counts_key="IMG_TIR1", lut_key="IMG_TIR1_TEMP")


def test_insat_lut_requires_explicit_kelvin_units(tmp_path):
    path = tmp_path / "no-units.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("IMG_TIR1", data=np.array([[1]], dtype=np.uint16))
        handle.create_dataset("IMG_TIR1_TEMP", data=np.array([210.0, 240.0]))
    with pytest.raises(ValueError, match="units"):
        load_temperature_lut(path, counts_key="IMG_TIR1", lut_key="IMG_TIR1_TEMP")


def test_equitable_threat_score_uses_random_hit_adjustment():
    table = ContingencyTable(hits=20, misses=10, false_alarms=5, correct_negatives=65)
    assert equitable_threat_score(table) == pytest.approx(12.5 / 27.5)
    assert equitable_threat_score(ContingencyTable(0, 0, 0, 0)) is None
