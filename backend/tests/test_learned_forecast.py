"""Phase 7 inference contract and geospatial evidence gate."""

import hashlib

import h5py
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.grid_replay import REPLAY_PATH
from backend.app.services.model_registry import get_model_artifact
from backend.app.services.replay import telemetry_snapshot
from backend.app.services.learned_forecast import (
    get_learned_grid_forecast,
    load_issue_time_context,
    verify_checkpoint,
)


client = TestClient(app)


def test_registered_checkpoint_matches_best_model():
    artifact = get_model_artifact("convlstm-sevir-v0")
    assert artifact.architecture == "LightweightConvLSTM"
    assert artifact.status == "UNVALIDATED_PROTOTYPE"
    checkpoint = verify_checkpoint(artifact)
    best_model = checkpoint.parents[2] / "backend" / "ml" / "checkpoints" / "best_model.pth"
    assert hashlib.sha256(best_model.read_bytes()).hexdigest() == artifact.checkpoint_sha256


def test_issue_time_context_never_reads_future_frames(tmp_path):
    paths = [tmp_path / "first.h5", tmp_path / "second.h5"]
    for path, future_value in zip(paths, [0, 255], strict=True):
        with h5py.File(path, "w") as handle:
            values = np.zeros((1, 384, 384, 25), dtype=np.uint8)
            values[:, :, :, :13] = 127
            values[:, :, :, 13:] = future_value
            handle.create_dataset("vil", data=values)
    first = load_issue_time_context(paths[0], issue_index=12)
    second = load_issue_time_context(paths[1], issue_index=12)
    assert first.shape == (1, 1, 13, 384, 384)
    assert np.array_equal(first.numpy(), second.numpy())


def test_checkpoint_hash_mismatch_is_rejected(tmp_path):
    artifact = get_model_artifact("convlstm-sevir-v0")
    bad_checkpoint = tmp_path / "bad.pth"
    bad_checkpoint.write_bytes(b"not a registered checkpoint")
    with pytest.raises(ValueError, match="SHA-256"):
        verify_checkpoint(artifact, checkpoint_path=bad_checkpoint)


def test_learned_replay_maps_12_frames_to_pixel_tracks():
    forecast = get_learned_grid_forecast()
    assert forecast.evidence_status.value == "LEARNED_FORECAST"
    assert forecast.model_status == "UNVALIDATED_PROTOTYPE"
    assert forecast.input_shape == [1, 1, 13, 384, 384]
    assert forecast.output_shape == [1, 1, 12, 384, 384]
    assert forecast.georeferenced is False
    assert len(forecast.frames) == 12
    assert [frame.lead_minutes for frame in forecast.frames] == list(range(5, 65, 5))
    assert all(frame.width == frame.height == 96 for frame in forecast.frames)
    assert any(frame.cells for frame in forecast.frames)
    assert all(0 <= cell.centroid_x < 96 and 0 <= cell.centroid_y < 96
               for frame in forecast.frames for cell in frame.cells)


def test_learned_api_exposes_only_ungeoreferenced_model_output():
    response = client.get("/api/v1/replay/grid/learned")
    assert response.status_code == 200
    payload = response.json()
    assert payload["georeferenced"] is False
    assert payload["model_status"] == "UNVALIDATED_PROTOTYPE"
    assert payload["frames"][0]["lead_minutes"] == 5


def test_jaydev_query_cannot_claim_learned_eta_without_georeferencing():
    response = client.post("/api/v1/location/query", json={
        "geometry_type": "POINT",
        "geometry": {"longitude": 85.8245, "latitude": 20.2961},
        "issue_time": telemetry_snapshot().issue_time.isoformat(),
        "horizon_minutes": 60,
        "forecast_mode": "LEARNED",
    })
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "NOT_COMPUTABLE"
    assert payload["evidence_status"] == "LEARNED_FORECAST"
    assert payload["model_version"] == "convlstm-sevir-v0"
    assert payload["impacts"] == []
    assert "georeferenc" in payload["message"].lower()
