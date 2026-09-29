from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.location import EvidenceStatus, GeoPoint


class ObservedRadarFrame(BaseModel):
    event_id: str
    frame_id: str
    offset_minutes: int
    valid_time: str
    evidence_status: EvidenceStatus
    method: Literal["SYNTHETIC_GAUSSIAN_RASTERIZATION"] = "SYNTHETIC_GAUSSIAN_RASTERIZATION"
    field: Literal["SIMULATED_REFLECTIVITY"] = "SIMULATED_REFLECTIVITY"
    unit: Literal["dBZ"] = "dBZ"
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    southwest: GeoPoint
    northeast: GeoPoint
    values: list[list[float]]
