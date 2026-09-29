"""Issue-time forecasts scored only against later observations in replay bundles."""

from functools import lru_cache
from pathlib import Path

import cv2
import h5py
import numpy as np

from backend.app.core.config import settings
from backend.app.schemas.location import EvidenceStatus
from backend.app.schemas.verification import LeadVerification, VerificationReport
from backend.app.science.verification import ContingencyTable, categorical_scores, contingency_table
from backend.app.services.baseline_forecast import (
    DETECTION_THRESHOLD_DBZ,
    _SpatialGrid,
    _render_synthetic_reflectivity,
    get_baseline_forecast,
)
from backend.app.services.grid_replay import EVENT_ID, ISSUE_INDEX, REPLAY_PATH
from backend.app.services.replay import get_replay_session


def _report(
    *, event_id: str, source: str, evidence_status: EvidenceStatus, method: str,
    field: str, threshold: float, threshold_unit: str, georeferenced: bool,
    observation_source: str, leads: list[LeadVerification], limitations: list[str],
) -> VerificationReport:
    counts = ContingencyTable(
        hits=sum(lead.hits for lead in leads),
        misses=sum(lead.misses for lead in leads),
        false_alarms=sum(lead.false_alarms for lead in leads),
        correct_negatives=sum(lead.correct_negatives for lead in leads),
    )
    scores = categorical_scores(counts) if leads else None
    return VerificationReport(
        event_id=event_id,
        source=source,
        status="COMPUTED" if scores and scores.csi is not None and scores.pod is not None else "UNVALIDATED",
        evidence_status=evidence_status,
        method=method,
        field=field,
        threshold=threshold,
        threshold_unit=threshold_unit,
        georeferenced=georeferenced,
        observation_source=observation_source,
        leads=leads,
        hits=counts.hits,
        misses=counts.misses,
        false_alarms=counts.false_alarms,
        correct_negatives=counts.correct_negatives,
        csi=scores.csi if scores else None,
        pod=scores.pod if scores else None,
        limitations=limitations,
    )


def _lead_score(lead_minutes: int, table: ContingencyTable) -> LeadVerification:
    scores = categorical_scores(table)
    return LeadVerification(
        lead_minutes=lead_minutes,
        hits=table.hits,
        misses=table.misses,
        false_alarms=table.false_alarms,
        correct_negatives=table.correct_negatives,
        csi=scores.csi,
        pod=scores.pod,
    )


@lru_cache(maxsize=1)
def verify_synthetic_replay() -> VerificationReport:
    session = get_replay_session(settings.active_replay_event)
    if session is None or session.evidence_status != EvidenceStatus.SIMULATED:
        raise ValueError("An explicitly simulated replay is required for this verification.")
    forecast = get_baseline_forecast()
    if forecast.event_id != session.event_id or forecast.issue_time != session.issue_time:
        raise ValueError("Baseline forecast does not match the replay issue time.")
    grid = _SpatialGrid(center_lat=20.30, center_lon=85.82)
    rows, columns = np.mgrid[0:grid.size, 0:grid.size]
    future = {
        frame.valid_time: frame for frame in session.frames
        if not frame.available_at_issue_time and frame.valid_time > session.issue_time
    }
    leads: list[LeadVerification] = []
    for valid_time, frame in sorted(future.items()):
        lead_minutes = int((valid_time - session.issue_time).total_seconds() / 60)
        if not 0 < lead_minutes <= 60:
            continue
        cells = [cell for cell in forecast.forecast_cells if cell.valid_time == valid_time]
        if not cells:
            continue
        predicted = np.zeros((grid.size, grid.size), dtype=bool)
        for cell in cells:
            east_km, north_km = grid.geographic_to_local(cell.centroid)
            center_column, center_row = grid.local_to_pixel(east_km, north_km)
            radius_pixels = cell.equivalent_radius_km / grid.resolution_km
            predicted |= (columns - center_column) ** 2 + (rows - center_row) ** 2 <= radius_pixels ** 2
        observed = _render_synthetic_reflectivity(frame, grid) >= DETECTION_THRESHOLD_DBZ
        leads.append(_lead_score(lead_minutes, contingency_table(predicted, observed, threshold=0.5)))
    return _report(
        event_id=session.event_id, source="SYNTHETIC", evidence_status=EvidenceStatus.SIMULATED,
        method=forecast.method, field="SIMULATED_REFLECTIVITY_FOOTPRINT",
        threshold=DETECTION_THRESHOLD_DBZ, threshold_unit="dBZ", georeferenced=True,
        observation_source="FUTURE_SYNTHETIC_REPLAY_FRAMES",
        leads=leads,
        limitations=[
            "Retrospective score over matched future simulation frames only; not operational or independently validated.",
            "Predicted constant-radius cell footprints are compared with simulated reflectivity >= 30 dBZ on a 1 km grid.",
            "No future observation is used to generate the issue-time baseline forecast.",
        ],
    )


def verify_sevir_optical_flow(path: Path = REPLAY_PATH, *, issue_index: int = ISSUE_INDEX) -> VerificationReport:
    with h5py.File(path, "r") as handle:
        vil = handle["vil"]
        if vil.ndim != 4 or vil.shape[0] != 1 or issue_index < 1 or issue_index >= vil.shape[-1]:
            raise ValueError("SEVIR VIL must have shape (1, height, width, time) with two issue-time frames.")
        previous = vil[0, :, :, issue_index - 1].astype(np.uint8)
        current = vil[0, :, :, issue_index].astype(np.uint8)
        flow = cv2.calcOpticalFlowFarneback(previous, current, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        height, width = current.shape
        columns, rows = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
        leads: list[LeadVerification] = []
        for step in range(1, min(12, vil.shape[-1] - issue_index - 1) + 1):
            forecast = cv2.remap(
                current,
                columns - flow[:, :, 0] * step,
                rows - flow[:, :, 1] * step,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            observed = vil[0, :, :, issue_index + step]
            leads.append(_lead_score(step * 5, contingency_table(forecast, observed, threshold=128)))
    return _report(
        event_id=EVENT_ID, source="SEVIR", evidence_status=EvidenceStatus.DATASET_VERIFIED,
        method="FARNEBACK_OPTICAL_FLOW_ADVECTION", field="SEVIR_VIL",
        threshold=128, threshold_unit="SEVIR_UINT8", georeferenced=False,
        observation_source="LATER_SEVIR_VIL_FRAMES",
        leads=leads,
        limitations=[
            "Single-event retrospective pixel-space benchmark; not a ConvLSTM score or India forecast skill.",
            "Flow is estimated only from the two frames at/before issue time; later VIL frames are scoring targets only.",
            "No WGS84 georeferencing, operational validation, or location ETA is supplied by this benchmark.",
        ],
    )


@lru_cache(maxsize=1)
def get_sevir_verification() -> VerificationReport:
    return verify_sevir_optical_flow()
