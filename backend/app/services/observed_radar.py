"""Geo-tagged raster of the declared simulation fixture, never an IMD observation."""

from functools import lru_cache

from backend.app.core.config import settings
from backend.app.schemas.location import EvidenceStatus
from backend.app.schemas.observed_radar import ObservedRadarFrame
from backend.app.services.baseline_forecast import _SpatialGrid, _render_synthetic_reflectivity
from backend.app.services.replay import get_replay_session


@lru_cache(maxsize=12)
def get_observed_radar_frame(offset_minutes: int) -> ObservedRadarFrame:
    session = get_replay_session(settings.active_replay_event)
    if session is None or session.evidence_status != EvidenceStatus.SIMULATED:
        raise ValueError("A georeferenced simulation replay is required.")
    frame = next((item for item in session.frames if item.offset_minutes == offset_minutes), None)
    if frame is None:
        raise LookupError(f"No observed replay frame at T{offset_minutes:+d} minutes.")
    grid = _SpatialGrid(center_lat=20.30, center_lon=85.82)
    field = _render_synthetic_reflectivity(frame, grid)
    southwest = grid.local_to_geographic(*grid.pixel_to_local(-0.5, grid.size - 0.5))
    northeast = grid.local_to_geographic(*grid.pixel_to_local(grid.size - 0.5, -0.5))
    return ObservedRadarFrame(
        event_id=session.event_id, frame_id=frame.frame_id, offset_minutes=offset_minutes,
        valid_time=frame.valid_time.isoformat(), evidence_status=EvidenceStatus.SIMULATED,
        width=grid.size, height=grid.size, southwest=southwest, northeast=northeast,
        values=field.round(2).tolist(),
    )
