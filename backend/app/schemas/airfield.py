from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.location import GeoPoint


class RunwayGeometry(BaseModel):
    aerodrome: Literal["VEBS"] = "VEBS"
    runway: Literal["14/32"] = "14/32"
    threshold_14: GeoPoint
    threshold_32: GeoPoint
    midpoint: GeoPoint
    approach_14: GeoPoint
    approach_32: GeoPoint
    approach_distance_km: float = 3
    true_bearing_14_deg: float
    source: str
    source_date: str


class WindVector(BaseModel):
    east_m_s: float = Field(ge=-100, le=100)
    north_m_s: float = Field(ge=-100, le=100)


class WindShearQuery(BaseModel):
    runway_direction: Literal["14", "32"]
    approach_wind: WindVector
    runway_wind: WindVector
    source_description: str = Field(min_length=3)


class WindShearResult(BaseModel):
    status: Literal["USER_SUPPLIED_CALCULATION"] = "USER_SUPPLIED_CALCULATION"
    runway_direction: Literal["14", "32"]
    approach_headwind_m_s: float
    runway_headwind_m_s: float
    approach_crosswind_m_s: float
    runway_crosswind_m_s: float
    delta_headwind_m_s: float
    delta_vector_m_s: float
    delta_vector_kt: float
    threshold_m_s: float = 15
    threshold_exceeded: bool
    source_description: str
    limitation: str = "Operator-supplied vector difference only; not a measured LLWS alert or ATC instruction."
