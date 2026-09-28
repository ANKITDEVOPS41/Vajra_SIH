from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.location import EvidenceStatus, GeoPoint


class ReplaySource(BaseModel):
    source_id: str
    name: str
    modality: Literal["radar", "satellite", "lightning", "environmental", "gauge"]
    evidence_status: EvidenceStatus
    availability: Literal["AVAILABLE", "DEGRADED", "NOT_AVAILABLE"]
    quality_status: str
    freshness_minutes: int | None = Field(default=None, ge=0)
    provenance: str


class ReplayEvent(BaseModel):
    source_id: str
    level: Literal["INFO", "WATCH", "WARNING", "CRITICAL"]
    message: str


class ReplayCell(BaseModel):
    cell_id: str
    centroid: GeoPoint
    max_reflectivity_dbz: float = Field(..., ge=0)
    rain_rate_mm_h: float = Field(..., ge=0)
    lightning_flashes: int = Field(..., ge=0)
    lifecycle_state: Literal[
        "INITIATING",
        "DEVELOPING",
        "INTENSIFYING",
        "MATURE",
        "WEAKENING",
        "DISSIPATING",
    ]


class ReplayFrame(BaseModel):
    frame_id: str
    offset_minutes: int
    valid_time: datetime
    record_type: Literal["OBSERVATION"]
    available_at_issue_time: bool
    cells: list[ReplayCell]
    events: list[ReplayEvent]


class ReplayMetrics(BaseModel):
    csi: float | None = Field(default=None, ge=0, le=1)
    pod: float | None = Field(default=None, ge=0, le=1)
    far: float | None = Field(default=None, ge=0, le=1)


class ReplayProvenance(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    dataset_id: str
    dataset_version: str
    created_for: str
    model_version: str | None = None
    code_version: str


class ReplaySession(BaseModel):
    schema_version: str
    event_id: str
    label: str
    region: str
    mode: Literal["REPLAY"]
    evidence_status: EvidenceStatus
    coordinate_reference_system: str
    starts_at: datetime
    issue_time: datetime
    ends_at: datetime
    timeline_step_minutes: int = Field(..., gt=0)
    horizon_minutes: int = Field(..., ge=0, le=360)
    verification_status: Literal["NOT_EVALUATED", "EVALUATED"]
    metrics: ReplayMetrics
    sources: list[ReplaySource]
    frames: list[ReplayFrame]
    provenance: ReplayProvenance
    limitations: list[str]


class TelemetrySnapshot(BaseModel):
    event_id: str
    mode: Literal["REPLAY"]
    evidence_status: EvidenceStatus
    issue_time: datetime
    horizon_minutes: int
    frame_count: int
    available_sources: int
    total_sources: int
    verification_status: Literal["NOT_EVALUATED", "EVALUATED"]
    csi: float | None
    pod: float | None
