import json
from functools import lru_cache
from pathlib import Path

from backend.app.core.config import settings
from backend.app.schemas.replay import ReplaySession, TelemetrySnapshot


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = PROJECT_ROOT / "data" / "events"


def _event_path(event_id: str) -> Path:
    return EVENTS_DIR / f"{event_id}.json"


@lru_cache(maxsize=16)
def get_replay_session(event_id: str) -> ReplaySession | None:
    path = _event_path(event_id)
    if not path.is_file():
        return None
    return ReplaySession.model_validate_json(path.read_text(encoding="utf-8"))


def list_replay_sessions() -> list[ReplaySession]:
    sessions: list[ReplaySession] = []
    for path in sorted(EVENTS_DIR.glob("*.json")):
        sessions.append(ReplaySession.model_validate_json(path.read_text(encoding="utf-8")))
    return sessions


def telemetry_snapshot() -> TelemetrySnapshot:
    session = get_replay_session(settings.active_replay_event)
    if session is None:
        raise FileNotFoundError(f"Active replay event '{settings.active_replay_event}' was not found.")

    available_sources = sum(source.availability == "AVAILABLE" for source in session.sources)
    return TelemetrySnapshot(
        event_id=session.event_id,
        mode=session.mode,
        evidence_status=session.evidence_status,
        issue_time=session.issue_time,
        horizon_minutes=session.horizon_minutes,
        frame_count=len(session.frames),
        available_sources=available_sources,
        total_sources=len(session.sources),
        verification_status=session.verification_status,
        csi=session.metrics.csi,
        pod=session.metrics.pod,
    )


def serialized_session(event_id: str) -> str | None:
    """Stable serialization used by determinism tests and offline packaging."""
    session = get_replay_session(event_id)
    if session is None:
        return None
    return json.dumps(session.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
