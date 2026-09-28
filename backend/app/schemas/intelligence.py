"""Evidence-gated modality and hazard telemetry for the replay dashboard."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.location import EvidenceStatus


class ModalityChannel(BaseModel):
    source_id: Literal["SEVIR_VIL", "SEVIR_IR107", "INSAT_3D_IR"]
    availability: Literal["AVAILABLE", "NOT_AVAILABLE"]
    role: Literal["MODEL_INPUT", "CONTEXT_ONLY", "UNAVAILABLE"]
    evidence_status: EvidenceStatus | None
    aligned_context_frames: int = Field(ge=0)
    reason: str


class MultimodalStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    event_id: str
    issue_frame_index: int
    fusion_mode: Literal["VIL_ONLY_FALLBACK"]
    model_input_channels: list[Literal["SEVIR_VIL"]]
    modalities: list[ModalityChannel]


class HazardIndicator(BaseModel):
    cell_id: str
    lead_minutes: int = Field(ge=0, le=60)
    indicator: Literal["HIGH_REFLECTIVITY_CORE", "NORMALIZED_VIL_CORE", "CLOUDBURST_RISK", "HAIL_RISK"]
    state: Literal["THRESHOLD_MET", "BELOW_THRESHOLD", "NOT_EVALUABLE"]
    value: float | None
    threshold: float | None
    unit: str | None
    method: str
    evidence_status: EvidenceStatus
    derivation_status: Literal[EvidenceStatus.INFERRED]
    uncertainty_status: Literal["NOT_CALIBRATED"]
    probability: None = None
    reason: str


class HazardScreening(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    event_id: str
    forecast_mode: Literal["BASELINE", "LEARNED"]
    modality_mode: Literal["VIL_ONLY_FALLBACK", "SIMULATED_RADAR_ONLY"]
    georeferenced: bool
    model_version: str | None
    model_status: str | None
    indicators: list[HazardIndicator]
    limitations: list[str]
