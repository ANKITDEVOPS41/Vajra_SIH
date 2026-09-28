from typing import Literal

from fastapi import APIRouter, HTTPException

from backend.app.schemas.forecast import BaselineForecast, GridAnalysis
from backend.app.schemas.intelligence import HazardScreening, MultimodalStatus
from backend.app.schemas.replay_grid import GridReplayFrame, GridReplayMetadata, LearnedGridForecast
from backend.app.schemas.replay import ReplaySession, TelemetrySnapshot
from backend.app.services.baseline_forecast import get_baseline_forecast
from backend.app.services.grid_analysis import analyze_grid_replay
from backend.app.services.grid_replay import grid_replay_metadata, load_grid_replay_frame
from backend.app.services.intelligence import assess_hazards, modality_status
from backend.app.services.replay import get_replay_session, list_replay_sessions, telemetry_snapshot

router = APIRouter()


@router.get("/sessions", response_model=list[ReplaySession])
def sessions() -> list[ReplaySession]:
    return list_replay_sessions()


@router.get("/sessions/{event_id}", response_model=ReplaySession)
def session(event_id: str) -> ReplaySession:
    replay = get_replay_session(event_id)
    if replay is None:
        raise HTTPException(status_code=404, detail=f"Replay event '{event_id}' was not found.")
    return replay


@router.get("/telemetry", response_model=TelemetrySnapshot)
def telemetry() -> TelemetrySnapshot:
    return telemetry_snapshot()


@router.get("/modalities", response_model=MultimodalStatus)
def modalities() -> MultimodalStatus:
    return modality_status()


@router.get("/hazards", response_model=HazardScreening)
def hazards(forecast_mode: Literal["BASELINE", "LEARNED"] = "BASELINE") -> HazardScreening:
    try:
        return assess_hazards(forecast_mode)
    except (ImportError, FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/grid", response_model=GridReplayMetadata)
def grid_replay() -> GridReplayMetadata:
    return grid_replay_metadata()


@router.get("/grid/frames/{frame_index}", response_model=GridReplayFrame)
def grid_replay_frame(frame_index: int) -> GridReplayFrame:
    try:
        return load_grid_replay_frame(frame_index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/baseline", response_model=BaselineForecast)
def baseline_forecast() -> BaselineForecast:
    return get_baseline_forecast()


@router.get("/grid/analysis/{frame_index}", response_model=GridAnalysis)
def grid_analysis(frame_index: int) -> GridAnalysis:
    try:
        return analyze_grid_replay(frame_index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/grid/learned", response_model=LearnedGridForecast)
def learned_grid_forecast() -> LearnedGridForecast:
    try:
        from backend.app.services.learned_forecast import get_learned_grid_forecast

        return get_learned_grid_forecast()
    except (ImportError, FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
