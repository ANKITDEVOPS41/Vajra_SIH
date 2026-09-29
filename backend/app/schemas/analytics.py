from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.schemas.location import EvidenceStatus, GeoPoint, LocationQueryResult


class AssetFeature(BaseModel):
    type: Literal["Feature"]
    id: str | int | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any]


class AssetFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[AssetFeature] = Field(min_length=1, max_length=100)


class AssetTriageRequest(BaseModel):
    feature_collection: AssetFeatureCollection
    issue_time: datetime
    horizon_minutes: int = Field(default=60, ge=30, le=360)
    forecast_mode: Literal["BASELINE", "LEARNED"] = "BASELINE"


class AssetTriageEntry(BaseModel):
    asset_id: str
    name: str
    centroid: GeoPoint
    geometry_type: Literal["POINT", "POLYGON", "ROUTE"]
    eta_status: Literal["ARRIVED", "COMPUTED", "UNKNOWN", "NOT_COMPUTABLE"]
    eta_minutes: float | None
    result: LocationQueryResult


class AssetTriageReport(BaseModel):
    issue_time: datetime
    status: Literal["COMPUTED", "PARTIAL", "NOT_COMPUTABLE"]
    evidence_status: EvidenceStatus
    method: str
    assets: list[AssetTriageEntry]


class IsochroneBand(BaseModel):
    lead_minutes: Literal[10, 20, 30]
    valid_time: datetime
    area_km2: float = Field(gt=0)
    geometry: dict[str, Any]
    method: str
    evidence_status: EvidenceStatus
    source_ids: list[str]
    forecast_ids: list[str]


class IsochroneReport(BaseModel):
    status: Literal["COMPUTED", "NOT_COMPUTABLE"]
    issue_time: datetime | None
    evidence_status: EvidenceStatus
    method: str
    bands: list[IsochroneBand]
    message: str


class IntensificationCell(BaseModel):
    cell_id: str
    previous_frame_id: str
    current_frame_id: str
    delta_dbz: float
    interval_minutes: float = Field(gt=0)
    rate_dbz_per_hour: float
    tag: Literal["RAPID_INTENSIFICATION"] | None


class IntensificationReport(BaseModel):
    status: Literal["COMPUTED", "NOT_COMPUTABLE"]
    evidence_status: EvidenceStatus
    method: str
    frame_index: int
    valid_time: datetime | None
    threshold_dbz_per_hour: float
    observation_role: str
    cells: list[IntensificationCell]
    message: str
