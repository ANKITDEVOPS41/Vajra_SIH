"""
backend/app/schemas/location.py
================================
Pydantic models for the VAJRA Location Intelligence Engine.

Implements Sections 5.2 and 5.3 of PRD V2:
  - LocationQuery  : the spatial + temporal query submitted by a user
  - LocationImpact : what the forecast engine returns for a query against
                     an active convective-cell track

Truth rule (PRD §0): every output carries issue_time, valid_time, method
and evidence_status so the jury can trace "where did this number come from?"
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations (controlled vocabularies)
# ---------------------------------------------------------------------------

class GeometryType(str, Enum):
    """Spatial representation of the query target (PRD §5.2)."""
    POINT   = "POINT"
    POLYGON = "POLYGON"
    ROUTE   = "ROUTE"


class CoordinateReferenceSystem(str, Enum):
    """Supported CRS.  WGS84 is the mandatory default (EPSG:4326)."""
    WGS84    = "EPSG:4326"
    WGS84_3D = "EPSG:4979"   # with ellipsoidal height (future use)


class EvidenceStatus(str, Enum):
    """
    Classification of how the output was produced (PRD §10).
    Prevents the UI from presenting simulated/inferred data as observed fact.
    """
    OBSERVED           = "OBSERVED"
    INFERRED           = "INFERRED"
    BASELINE_FORECAST  = "BASELINE_FORECAST"
    LEARNED_FORECAST   = "LEARNED_FORECAST"
    SIMULATED          = "SIMULATED"        # synthetic / demo data
    DEGRADED           = "DEGRADED"         # stale / missing source fallback


class SpatialRelation(str, Enum):
    """Topological relationship between the convective hazard and query geometry."""
    INTERSECTS    = "INTERSECTS"
    WITHIN        = "WITHIN"
    APPROACHING   = "APPROACHING"   # not yet intersecting but on trajectory
    RECEDING      = "RECEDING"
    NO_RELATION   = "NO_RELATION"


class ETAStatus(str, Enum):
    """
    Explicit states for ETA (PRD §5.4).
    UNKNOWN          – no intersection with geometry exists in the forecast horizon.
    NOT_COMPUTABLE   – an intersection may exist but trajectory data are insufficient
                       (missing continuity, low track confidence, geometry mismatch).
    ARRIVED          – cell already overlaps the geometry at issue time.
    COMPUTED         – a defensible ETA has been derived from forecast intersection.
    """
    UNKNOWN        = "UNKNOWN"
    NOT_COMPUTABLE = "NOT_COMPUTABLE"
    ARRIVED        = "ARRIVED"
    COMPUTED       = "COMPUTED"


class HazardType(str, Enum):
    MAX_REFLECTIVITY_DBZ  = "MAX_REFLECTIVITY_DBZ"
    QPE_MM_PER_HOUR       = "QPE_MM_PER_HOUR"
    VIL_KG_PER_M2         = "VIL_KG_PER_M2"
    LIGHTNING_FLASH_RATE  = "LIGHTNING_FLASH_RATE"
    HAIL_PROBABILITY      = "HAIL_PROBABILITY"       # requires evidence gate
    DOWNBURST_PROBABILITY = "DOWNBURST_PROBABILITY"  # requires evidence gate
    CELL_SEVERITY_INDEX   = "CELL_SEVERITY_INDEX"    # composite, unitless 0-1


# ---------------------------------------------------------------------------
# Geometry payload helpers
# ---------------------------------------------------------------------------

class PointGeometry(BaseModel):
    """GeoJSON-compatible point [lon, lat] in the configured CRS."""
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude (decimal degrees WGS84)")
    latitude:  float = Field(..., ge=-90.0,  le=90.0,  description="Latitude  (decimal degrees WGS84)")

    @field_validator("longitude")
    @classmethod
    def lon_must_be_finite(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("longitude must be finite")
        return v

    @field_validator("latitude")
    @classmethod
    def lat_must_be_finite(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("latitude must be finite")
        return v


class RouteGeometry(BaseModel):
    """Ordered list of named waypoints forming a polyline corridor."""
    waypoints: List[PointGeometry] = Field(
        ..., min_length=2, description="Ordered sequence of at least 2 waypoints"
    )
    waypoint_names: Optional[List[str]] = Field(
        default=None,
        description="Human-readable labels aligned 1-to-1 with waypoints"
    )

    @model_validator(mode="after")
    def names_match_waypoints(self) -> "RouteGeometry":
        if self.waypoint_names is not None and len(self.waypoint_names) != len(self.waypoints):
            raise ValueError("waypoint_names must have the same length as waypoints")
        return self


class PolygonGeometry(BaseModel):
    """
    Exterior ring as an ordered list of points (implicitly closed).
    Minimum 3 distinct vertices.
    """
    vertices: List[PointGeometry] = Field(
        ..., min_length=3, description="Exterior ring vertices (open polygon)"
    )


# ---------------------------------------------------------------------------
# Section 5.2 — LocationQuery
# ---------------------------------------------------------------------------

class LocationQuery(BaseModel):
    """
    PRD §5.2 — Input query submitted to the Location Intelligence Engine.

    The geometry field accepts one of:
      - PointGeometry   when geometry_type = POINT
      - PolygonGeometry when geometry_type = POLYGON
      - RouteGeometry   when geometry_type = ROUTE
    """

    # ---- identity -------------------------------------------------------
    query_id:   str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique query identifier (UUID v4 auto-generated if omitted)"
    )

    # ---- geometry -------------------------------------------------------
    geometry_type: GeometryType = Field(
        ..., description="Spatial representation of the query target"
    )
    geometry: Dict[str, Any] = Field(
        ...,
        description=(
            "Geometry payload.  Must be a serialised PointGeometry, "
            "PolygonGeometry or RouteGeometry matching geometry_type."
        )
    )
    coordinate_reference_system: CoordinateReferenceSystem = Field(
        default=CoordinateReferenceSystem.WGS84,
        description="CRS for all coordinates in this query"
    )

    # ---- metadata -------------------------------------------------------
    name: Optional[str] = Field(
        default=None,
        description="Human-readable label (e.g. 'Jaydev Vihar Square, Bhubaneswar')"
    )
    source_of_location: Optional[str] = Field(
        default=None,
        description="How the location was provided: USER_SELECTED | GEOCODED | CORRIDOR_DRAWN | …"
    )

    # ---- temporal -------------------------------------------------------
    issue_time: datetime = Field(
        ...,
        description=(
            "The clock-frozen issue time (T0).  No forecast data after this "
            "timestamp may be used to compute the response (prevents leakage)."
        )
    )
    horizon_minutes: int = Field(
        default=360,
        ge=30,
        le=360,
        description="Forecast horizon in minutes from issue_time (30–360 min)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Wall-clock time the query object was instantiated"
    )

    @model_validator(mode="after")
    def geometry_matches_type(self) -> "LocationQuery":
        """Light structural validation that the geometry dict is consistent."""
        gtype = self.geometry_type
        geom  = self.geometry

        required_keys = {
            GeometryType.POINT:   {"longitude", "latitude"},
            GeometryType.POLYGON: {"vertices"},
            GeometryType.ROUTE:   {"waypoints"},
        }
        expected = required_keys[gtype]
        if not expected.issubset(geom.keys()):
            raise ValueError(
                f"geometry for type {gtype.value} must contain keys {expected}; "
                f"got {set(geom.keys())}"
            )
        return self

    model_config = {"json_schema_extra": {
        "examples": [{
            "geometry_type": "POINT",
            "geometry": {"longitude": 85.8245, "latitude": 20.2961},
            "name": "Jaydev Vihar Square, Bhubaneswar",
            "source_of_location": "USER_SELECTED",
            "issue_time": "2023-10-05T08:00:00Z",
            "horizon_minutes": 360
        }]
    }}


# ---------------------------------------------------------------------------
# Section 5.3 — LocationImpact
# ---------------------------------------------------------------------------

class ETAResult(BaseModel):
    """
    Structured ETA result (PRD §5.4).

    eta_minutes is populated ONLY when status == COMPUTED; otherwise it is
    None.  The method field records exactly which algorithm produced the
    estimate so every number is traceable.
    """
    status:      ETAStatus       = Field(..., description="Computational state of the ETA")
    eta_minutes: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Forecast arrival time in minutes from issue_time.  Null unless COMPUTED."
    )
    method: str = Field(
        default="NOT_ATTEMPTED",
        description=(
            "Computation method used; e.g. 'LINEAR_TRACK_INTERSECTION', "
            "'FIELD_CONTOUR_CROSSING', 'NOT_ATTEMPTED'"
        )
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Track confidence score [0–1] at the time of computation"
    )
    not_computable_reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation when status is NOT_COMPUTABLE or UNKNOWN"
    )

    @model_validator(mode="after")
    def eta_only_when_computed(self) -> "ETAResult":
        if self.status != ETAStatus.COMPUTED and self.eta_minutes is not None:
            raise ValueError(
                "eta_minutes must be None unless ETAStatus is COMPUTED"
            )
        if self.status == ETAStatus.COMPUTED and self.eta_minutes is None:
            raise ValueError(
                "eta_minutes is required when ETAStatus is COMPUTED"
            )
        return self


class UncertaintyBand(BaseModel):
    """Optional uncertainty quantification attached to a hazard value."""
    lower:  float = Field(..., description="Lower bound of the uncertainty range")
    upper:  float = Field(..., description="Upper bound of the uncertainty range")
    method: str   = Field(..., description="How uncertainty was derived (ENSEMBLE | SPECTRAL | NONE)")
    level:  float = Field(default=0.90, ge=0.0, le=1.0, description="Confidence level")


class LocationImpact(BaseModel):
    """
    PRD §5.3 — Output record from the Location Intelligence Engine for a
    single (query, cell, valid_time) triplet.

    One LocationQuery may generate many LocationImpact records — one per
    cell per forecast time step in the 0–6 h horizon.
    """

    # ---- identity -------------------------------------------------------
    query_id:    str = Field(..., description="Back-reference to the originating LocationQuery")
    impact_id:   str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this impact record"
    )

    # ---- temporal -------------------------------------------------------
    valid_time:  datetime = Field(
        ...,
        description="The forecast valid time this record describes (T0 + lead)"
    )
    lead_minutes: int = Field(
        ..., ge=0,
        description="Lead time in whole minutes (valid_time - issue_time)"
    )

    # ---- cell reference -------------------------------------------------
    cell_id: str = Field(
        ...,
        description="Identifier of the convective cell tracked by the state engine"
    )

    # ---- hazard payload -------------------------------------------------
    hazard:  HazardType    = Field(..., description="Physical quantity being reported")
    value:   Optional[float] = Field(
        default=None,
        description="Scalar hazard value.  None if the cell lacks sufficient data."
    )
    unit:    str           = Field(..., description="SI/meteorological unit of the hazard value")
    uncertainty: Optional[UncertaintyBand] = Field(
        default=None,
        description="Optional uncertainty band around the reported value"
    )

    # ---- provenance & evidence ------------------------------------------
    method:          str           = Field(
        ..., description="Algorithm that produced this impact record"
    )
    evidence_status: EvidenceStatus = Field(
        ...,
        description=(
            "OBSERVED | INFERRED | BASELINE_FORECAST | LEARNED_FORECAST | "
            "SIMULATED | DEGRADED"
        )
    )
    source_ids: List[str] = Field(
        default_factory=list,
        description="IDs of source records (radar scans, satellite frames, …) used"
    )
    forecast_id:   Optional[str] = Field(
        default=None,
        description="Identifier of the forecast run that produced this impact"
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Model / algorithm version tag (e.g. 'optical_flow_v1.2')"
    )

    # ---- spatial relationship -------------------------------------------
    spatial_relation: SpatialRelation = Field(
        ..., description="Topological relationship between cell hazard footprint and query geometry"
    )
    distance_km: Optional[float] = Field(
        default=None,
        ge=0.0,
        description=(
            "Great-circle distance in km from query geometry centroid to "
            "nearest hazard boundary.  0.0 when WITHIN or INTERSECTS."
        )
    )

    # ---- ETA (PRD §5.4 — the flagship field) ----------------------------
    eta: ETAResult = Field(
        ...,
        description="Structured ETA result (see ETAResult).  Never a raw number without metadata."
    )

    # ---- convenience accessor -------------------------------------------
    @property
    def eta_minutes(self) -> Optional[float]:
        """Shorthand; None if ETA is not COMPUTED."""
        return self.eta.eta_minutes

    model_config = {"json_schema_extra": {
        "examples": [{
            "query_id": "550e8400-e29b-41d4-a716-446655440000",
            "valid_time": "2023-10-05T09:00:00Z",
            "lead_minutes": 60,
            "cell_id": "CELL_042",
            "hazard": "MAX_REFLECTIVITY_DBZ",
            "value": 52.3,
            "unit": "dBZ",
            "method": "OPTICAL_FLOW_ADVECTION",
            "evidence_status": "BASELINE_FORECAST",
            "spatial_relation": "APPROACHING",
            "distance_km": 12.4,
            "eta": {
                "status": "COMPUTED",
                "eta_minutes": 47.2,
                "method": "LINEAR_TRACK_INTERSECTION",
                "confidence": 0.72
            }
        }]
    }}
