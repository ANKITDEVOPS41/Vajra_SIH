from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.location import EvidenceStatus


class LeadVerification(BaseModel):
    lead_minutes: int = Field(gt=0, le=60)
    hits: int = Field(ge=0)
    misses: int = Field(ge=0)
    false_alarms: int = Field(ge=0)
    correct_negatives: int = Field(ge=0)
    csi: float | None = Field(default=None, ge=0, le=1)
    pod: float | None = Field(default=None, ge=0, le=1)


class VerificationReport(BaseModel):
    event_id: str
    source: Literal["SYNTHETIC", "SEVIR"]
    status: Literal["COMPUTED", "UNVALIDATED"]
    forecast_validation_status: Literal["UNVALIDATED"] = "UNVALIDATED"
    verification_scope: Literal["RETROSPECTIVE_REPLAY"] = "RETROSPECTIVE_REPLAY"
    evidence_status: EvidenceStatus
    method: str
    field: str
    threshold: float
    threshold_unit: str
    georeferenced: bool
    observation_source: str
    leads: list[LeadVerification]
    hits: int = Field(ge=0)
    misses: int = Field(ge=0)
    false_alarms: int = Field(ge=0)
    correct_negatives: int = Field(ge=0)
    csi: float | None = Field(default=None, ge=0, le=1)
    pod: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str]
