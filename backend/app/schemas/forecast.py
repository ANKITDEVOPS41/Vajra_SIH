from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.location import EvidenceStatus, GeoPoint


class DetectedCellGeometry(BaseModel):
    cell_id: str
    centroid: GeoPoint
    polygon: list[GeoPoint] = Field(min_length=3)
    area_km2: float = Field(gt=0)
    equivalent_radius_km: float = Field(gt=0)
    max_reflectivity_dbz: float = Field(ge=0)
    qc_removed_pixels: int = Field(ge=0)


class CellTrackSnapshot(BaseModel):
    cell_id: str
    age_scans: int = Field(ge=1)
    centroid: GeoPoint
    speed_kmh: float = Field(ge=0)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    trajectory: list[GeoPoint]


class ForecastCell(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    forecast_id: str
    cell_id: str
    lead_minutes: int = Field(gt=0, le=60)
    valid_time: datetime
    centroid: GeoPoint
    polygon: list[GeoPoint] = Field(min_length=3)
    equivalent_radius_km: float = Field(gt=0)
    max_reflectivity_dbz: float = Field(ge=0)
    method: str
    evidence_status: EvidenceStatus
    model_version: str | None = None
    source_ids: list[str]


class BaselineForecast(BaseModel):
    event_id: str
    issue_time: datetime
    evidence_status: EvidenceStatus
    mode: Literal["REPLAY"]
    method: Literal["CONSTANT_VELOCITY_EQUIVALENT_AREA"]
    detection_threshold_dbz: float
    tracks: list[CellTrackSnapshot]
    current_cells: list[DetectedCellGeometry]
    forecast_cells: list[ForecastCell]
    source_ids: list[str]
    limitations: list[str]


class UngeoreferencedGridCell(BaseModel):
    cell_id: str
    centroid_x: float
    centroid_y: float
    area_pixels: int = Field(gt=0)
    peak_value: int = Field(ge=0, le=255)


class GridAnalysis(BaseModel):
    event_id: str
    frame_index: int = Field(ge=0)
    evidence_status: EvidenceStatus
    georeferenced: Literal[False]
    field_units: Literal["SEVIR_UINT8"]
    quality_control_status: Literal["TEXTURE_SCREEN_NON_PHYSICAL"]
    cells: list[UngeoreferencedGridCell]
    limitations: list[str]
