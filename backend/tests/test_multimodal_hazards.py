"""Phase 8-9 modality fallback and evidence-gated hazard screens."""

import h5py
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.intelligence import assess_hazards, modality_status


client = TestClient(app)


def test_vil_only_replay_reports_missing_thermal_channel(tmp_path):
    path = tmp_path / "vil-only.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("vil", data=np.zeros((1, 2, 2, 13), dtype=np.uint8))
        handle.create_dataset("id", data=[b"sample-1"])

    result = modality_status(path)
    assert result.fusion_mode == "VIL_ONLY_FALLBACK"
    assert result.model_input_channels == ["SEVIR_VIL"]
    assert result.modalities[0].availability == "AVAILABLE"
    assert result.modalities[0].aligned_context_frames == 13
    assert result.modalities[1].source_id == "SEVIR_IR107"
    assert result.modalities[1].availability == "NOT_AVAILABLE"
    assert result.modalities[1].aligned_context_frames == 0
    assert result.modalities[2].source_id == "INSAT_3D_IR"
    assert result.modalities[2].availability == "NOT_AVAILABLE"
    assert not any(modality.role == "MODEL_INPUT" and modality.source_id != "SEVIR_VIL" for modality in result.modalities)


def test_unaligned_ir107_is_context_only_and_never_fused(tmp_path):
    path = tmp_path / "unaligned-ir.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("vil", data=np.zeros((1, 2, 2, 13), dtype=np.uint8))
        handle.create_dataset("ir107", data=np.zeros((1, 2, 2, 12), dtype=np.uint8))
    result = modality_status(path)
    ir = result.modalities[1]
    assert ir.availability == "AVAILABLE"
    assert ir.role == "CONTEXT_ONLY"
    assert ir.aligned_context_frames == 0
    assert "not verified" in ir.reason.lower()


def test_matching_ir107_shape_still_does_not_imply_verified_alignment(tmp_path):
    path = tmp_path / "matching-shape-ir.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("vil", data=np.zeros((1, 2, 2, 13), dtype=np.uint8))
        handle.create_dataset("ir107", data=np.zeros((1, 2, 2, 13), dtype=np.uint8))
    ir = modality_status(path).modalities[1]
    assert ir.availability == "AVAILABLE"
    assert ir.aligned_context_frames == 0
    assert ir.role == "CONTEXT_ONLY"


def test_hazard_screens_show_methods_evidence_and_withhold_risks():
    baseline = assess_hazards("BASELINE")
    assert baseline.modality_mode == "SIMULATED_RADAR_ONLY"
    core = next(item for item in baseline.indicators if item.indicator == "HIGH_REFLECTIVITY_CORE" and item.lead_minutes == 0)
    assert core.state == "THRESHOLD_MET"
    assert core.evidence_status.value == "SIMULATED"
    assert core.derivation_status.value == "INFERRED"
    assert core.threshold == 45.0
    assert core.unit == "dBZ"
    assert core.method == "CELL_PEAK_DBZ_GE_45"
    assert core.probability is None
    assert core.uncertainty_status == "NOT_CALIBRATED"
    for risk in ("CLOUDBURST_RISK", "HAIL_RISK"):
        withheld = next(item for item in baseline.indicators if item.indicator == risk and item.lead_minutes == 0)
        assert withheld.state == "NOT_EVALUABLE"
        assert withheld.value is None
        assert withheld.probability is None


def test_learned_hazards_remain_pixel_space_and_not_physical_risk():
    learned = assess_hazards("LEARNED")
    assert learned.georeferenced is False
    assert learned.model_version == "convlstm-sevir-v0"
    assert learned.model_status == "UNVALIDATED_PROTOTYPE"
    assert learned.modality_mode == "VIL_ONLY_FALLBACK"
    core = next(item for item in learned.indicators if item.indicator == "NORMALIZED_VIL_CORE")
    assert core.unit == "normalized 0-1"
    assert core.threshold == 0.5
    assert core.evidence_status.value == "LEARNED_FORECAST"
    assert core.derivation_status.value == "INFERRED"
    assert all(item.probability is None for item in learned.indicators)
    assert all(item.state == "NOT_EVALUABLE" for item in learned.indicators if item.indicator in {"CLOUDBURST_RISK", "HAIL_RISK"})


def test_phase_8_9_api_contract():
    modalities = client.get("/api/v1/replay/modalities")
    assert modalities.status_code == 200
    assert modalities.json()["fusion_mode"] == "VIL_ONLY_FALLBACK"
    assert modalities.json()["modalities"][1]["availability"] == "NOT_AVAILABLE"

    hazards = client.get("/api/v1/replay/hazards", params={"forecast_mode": "BASELINE"})
    assert hazards.status_code == 200
    indicators = hazards.json()["indicators"]
    assert any(item["indicator"] == "HIGH_REFLECTIVITY_CORE" and item["state"] == "THRESHOLD_MET" for item in indicators)
    assert all(item["probability"] is None for item in indicators)
