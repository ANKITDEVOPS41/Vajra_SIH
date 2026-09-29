from pathlib import Path
from copy import deepcopy

import h5py
import numpy as np
from fastapi.testclient import TestClient

from backend.app.science.verification import ContingencyTable, categorical_scores
from backend.app.services.replay_verification import verify_sevir_optical_flow, verify_synthetic_replay
from backend.app.services.baseline_forecast import get_baseline_forecast
from backend.app.services.replay import get_replay_session
from backend.app.core.config import settings
from backend.main import app


client = TestClient(app)


def test_categorical_scores_returns_csi_and_pod():
    scores = categorical_scores(ContingencyTable(hits=2, misses=1, false_alarms=1, correct_negatives=6))
    assert scores.csi == 0.5
    assert scores.pod == 2 / 3


def test_synthetic_replay_verifies_only_matching_future_leads():
    report = verify_synthetic_replay()
    assert report.evidence_status == "SIMULATED"
    assert report.method == "CONSTANT_VELOCITY_EQUIVALENT_AREA"
    assert report.status == "COMPUTED"
    assert report.forecast_validation_status == "UNVALIDATED"
    assert [score.lead_minutes for score in report.leads] == [30, 60]
    assert report.csi is not None and 0 <= report.csi <= 1
    assert report.pod is not None and 0 <= report.pod <= 1
    assert report.georeferenced is True


def test_future_observation_affects_verification_not_issue_time_forecast(monkeypatch):
    baseline = get_baseline_forecast()
    original_score = verify_synthetic_replay().csi
    altered_session = deepcopy(get_replay_session(settings.active_replay_event))
    for frame in altered_session.frames:
        if not frame.available_at_issue_time:
            frame.cells = []
    monkeypatch.setattr(
        "backend.app.services.replay_verification.get_replay_session",
        lambda _event_id: altered_session,
    )
    verify_synthetic_replay.cache_clear()
    try:
        assert verify_synthetic_replay().csi != original_score
        assert get_baseline_forecast() is baseline
    finally:
        verify_synthetic_replay.cache_clear()


def _sevir_file(path: Path, future_event: bool = True) -> None:
    frames = np.zeros((1, 32, 32, 4), dtype=np.uint8)
    frames[0, 12:20, 12:20, 1] = 180
    frames[0, 12:20, 12:20, 2] = 180
    if future_event:
        frames[0, 12:20, 12:20, 3] = 180
    with h5py.File(path, "w") as handle:
        handle.create_dataset("vil", data=frames)


def test_sevir_optical_flow_verifies_pixel_grid_without_georeferencing(tmp_path: Path):
    path = tmp_path / "event.h5"
    _sevir_file(path)
    report = verify_sevir_optical_flow(path, issue_index=2)
    assert report.status == "COMPUTED"
    assert report.forecast_validation_status == "UNVALIDATED"
    assert report.evidence_status == "DATASET_VERIFIED"
    assert report.method == "FARNEBACK_OPTICAL_FLOW_ADVECTION"
    assert report.georeferenced is False
    assert [score.lead_minutes for score in report.leads] == [5]
    assert report.csi is not None


def test_sevir_without_future_observation_is_unvalidated(tmp_path: Path):
    path = tmp_path / "event.h5"
    _sevir_file(path)
    with h5py.File(path, "r+") as handle:
        values = handle["vil"][:, :, :, :3]
        del handle["vil"]
        handle.create_dataset("vil", data=values)
    report = verify_sevir_optical_flow(path, issue_index=2)
    assert report.status == "UNVALIDATED"
    assert report.csi is None and report.pod is None


def test_verification_api_keeps_sources_distinct():
    synthetic = client.get("/api/v1/replay/verification", params={"source": "SYNTHETIC"})
    sevir = client.get("/api/v1/replay/verification", params={"source": "SEVIR"})
    assert synthetic.status_code == sevir.status_code == 200
    assert synthetic.json()["evidence_status"] == "SIMULATED"
    assert sevir.json()["georeferenced"] is False
    assert sevir.json()["method"] == "FARNEBACK_OPTICAL_FLOW_ADVECTION"
