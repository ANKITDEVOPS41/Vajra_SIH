"""Replay-observation intensity derivative, isolated from forecast inference."""

from backend.app.core.config import settings
from backend.app.schemas.analytics import IntensificationCell, IntensificationReport
from backend.app.schemas.location import EvidenceStatus
from backend.app.services.replay import get_replay_session


RID_THRESHOLD_DBZ_PER_HOUR = 8.0
METHOD = "ADJACENT_SAME_CELL_MAX_DBZ_FINITE_DIFFERENCE"


def replay_intensification(frame_index: int, forecast_mode: str = "BASELINE") -> IntensificationReport:
    session = get_replay_session(settings.active_replay_event)
    if session is None:
        raise FileNotFoundError("Active replay event is unavailable")
    if not 0 <= frame_index < len(session.frames):
        raise IndexError("Replay frame index is out of range")
    current = session.frames[frame_index]
    if forecast_mode == "LEARNED":
        return IntensificationReport(
            status="NOT_COMPUTABLE", evidence_status=EvidenceStatus.LEARNED_FORECAST,
            method="NOT_ATTEMPTED_UNGEOREFERENCED_MODEL", frame_index=frame_index,
            valid_time=None, threshold_dbz_per_hour=RID_THRESHOLD_DBZ_PER_HOUR,
            observation_role="NONE", cells=[],
            message="The VIL-only ConvLSTM has no calibrated dBZ or India georeferencing.",
        )
    role = "ISSUE_TIME_OBSERVATION" if current.available_at_issue_time else "POST_ISSUE_REPLAY_OBSERVATION"
    if frame_index == 0:
        return IntensificationReport(
            status="NOT_COMPUTABLE", evidence_status=session.evidence_status,
            method=METHOD, frame_index=frame_index, valid_time=current.valid_time,
            threshold_dbz_per_hour=RID_THRESHOLD_DBZ_PER_HOUR,
            observation_role=role, cells=[], message="No previous observation exists for a derivative.",
        )
    previous = session.frames[frame_index - 1]
    elapsed = (current.valid_time - previous.valid_time).total_seconds() / 60
    if elapsed <= 0:
        raise ValueError("Replay observation times must strictly increase")
    previous_by_id = {cell.cell_id: cell for cell in previous.cells}
    cells = []
    for cell in current.cells:
        prior = previous_by_id.get(cell.cell_id)
        if prior is None:
            continue
        delta = cell.max_reflectivity_dbz - prior.max_reflectivity_dbz
        rate = delta * 60 / elapsed
        cells.append(IntensificationCell(
            cell_id=cell.cell_id, previous_frame_id=previous.frame_id,
            current_frame_id=current.frame_id, delta_dbz=round(delta, 3),
            interval_minutes=elapsed, rate_dbz_per_hour=round(rate, 3),
            tag="RAPID_INTENSIFICATION" if rate > RID_THRESHOLD_DBZ_PER_HOUR else None,
        ))
    return IntensificationReport(
        status="COMPUTED" if cells else "NOT_COMPUTABLE",
        evidence_status=session.evidence_status, method=METHOD, frame_index=frame_index,
        valid_time=current.valid_time, threshold_dbz_per_hour=RID_THRESHOLD_DBZ_PER_HOUR,
        observation_role=role, cells=cells,
        message="Finite difference of adjacent replay observations only; no future frame enters forecast inference."
        if cells else "No same-ID tracked cell appears in the adjacent observations.",
    )
