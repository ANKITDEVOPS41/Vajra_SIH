from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.location import EvidenceStatus


class ScorecardLead(BaseModel):
    lead_minutes: Literal[15, 30, 45, 60, 90, 120]
    status: Literal["COMPUTED", "NOT_COMPUTABLE"]
    hits: int | None = Field(default=None, ge=0)
    misses: int | None = Field(default=None, ge=0)
    false_alarms: int | None = Field(default=None, ge=0)
    correct_negatives: int | None = Field(default=None, ge=0)
    pod: float | None = Field(default=None, ge=0, le=1)
    far: float | None = Field(default=None, ge=0, le=1)
    csi: float | None = Field(default=None, ge=0, le=1)
    hss: float | None = Field(default=None, ge=-1, le=1)
    reason: str | None = None


class WmoScorecard(BaseModel):
    event_id: str
    source: Literal["SYNTHETIC", "SEVIR"]
    verification_scope: Literal["RETROSPECTIVE_REPLAY"] = "RETROSPECTIVE_REPLAY"
    forecast_validation_status: Literal["UNVALIDATED"] = "UNVALIDATED"
    evidence_status: EvidenceStatus
    method: str
    field: str
    threshold: float
    threshold_unit: str
    georeferenced: bool
    observation_source: str
    leads: list[ScorecardLead]
    limitations: list[str]
