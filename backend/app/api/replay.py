from typing import Literal

from fastapi import APIRouter, HTTPException

from backend.app.adapters.imd_adapter import IMDBridgeStatus, imd_bridge_status
from backend.app.schemas.analytics import IntensificationReport, IsochroneReport
from backend.app.schemas.forecast import BaselineForecast, GridAnalysis
from backend.app.schemas.intelligence import HazardScreening, MultimodalStatus
from backend.app.schemas.replay_grid import GridReplayFrame, GridReplayMetadata, LearnedGridForecast
from backend.app.schemas.replay import ReplaySession, TelemetrySnapshot
from backend.app.schemas.verification import VerificationReport
from backend.app.schemas.scorecard import WmoScorecard
from backend.app.schemas.observed_radar import ObservedRadarFrame
from backend.app.science.wmo_scorecard import build_wmo_scorecard
from backend.app.services.baseline_forecast import get_baseline_forecast
from backend.app.services.grid_analysis import analyze_grid_replay
from backend.app.services.grid_replay import grid_replay_metadata, load_grid_replay_frame
from backend.app.services.intelligence import assess_hazards, modality_status
from backend.app.services.intensification import replay_intensification
from backend.app.services.isochrones import build_isochrones
from backend.app.services.replay import get_replay_session, list_replay_sessions, telemetry_snapshot
from backend.app.services.replay_verification import get_sevir_verification, verify_synthetic_replay
from backend.app.services.observed_radar import get_observed_radar_frame

router = APIRouter()


@router.get("/isochrones", response_model=IsochroneReport)
def isochrones(forecast_mode: Literal["BASELINE", "LEARNED"] = "BASELINE") -> IsochroneReport:
    return build_isochrones(forecast_mode)


@router.get("/intensification", response_model=IntensificationReport)
def intensification(frame_index: int, forecast_mode: Literal["BASELINE", "LEARNED"] = "BASELINE") -> IntensificationReport:
    try:
        return replay_intensification(frame_index, forecast_mode)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/imd-bridge", response_model=IMDBridgeStatus)
def imd_bridge() -> IMDBridgeStatus:
    return imd_bridge_status()


@router.get("/verification", response_model=VerificationReport)
def verification(source: Literal["SYNTHETIC", "SEVIR"] = "SYNTHETIC") -> VerificationReport:
    try:
        return verify_synthetic_replay() if source == "SYNTHETIC" else get_sevir_verification()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/wmo-scorecard", response_model=WmoScorecard)
def wmo_scorecard(source: Literal["SYNTHETIC", "SEVIR"] = "SYNTHETIC") -> WmoScorecard:
    try:
        report = verify_synthetic_replay() if source == "SYNTHETIC" else get_sevir_verification()
        return build_wmo_scorecard(report)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/observed-radar/{offset_minutes}", response_model=ObservedRadarFrame)
def observed_radar(offset_minutes: int) -> ObservedRadarFrame:
    try:
        return get_observed_radar_frame(offset_minutes)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
