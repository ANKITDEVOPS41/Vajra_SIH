"""Published VEBS geometry and elementary runway-relative wind-vector math."""

from math import cos, hypot, radians, sin

from pyproj import Geod

from backend.app.schemas.airfield import RunwayGeometry, WindShearQuery, WindShearResult, WindVector
from backend.app.schemas.location import GeoPoint


_GEOD = Geod(ellps="WGS84")
_SOURCE = "https://aim-india.aai.aero/eaip/eaip-v2-04-2026/eAIP/IN-AD%202.1VEBS-en-GB.html"


def _dms(degrees: int, minutes: int, seconds: float) -> float:
    return degrees + minutes / 60 + seconds / 3600


def vebs_geometry() -> RunwayGeometry:
    threshold_14 = GeoPoint(lat=_dms(20, 15, 39.18), lon=_dms(85, 48, 18.22))
    threshold_32 = GeoPoint(lat=_dms(20, 14, 27.12), lon=_dms(85, 49, 14.00))
    bearing, _, distance_m = _GEOD.inv(threshold_14.lon, threshold_14.lat, threshold_32.lon, threshold_32.lat)
    mid_lon, mid_lat, _ = _GEOD.fwd(threshold_14.lon, threshold_14.lat, bearing, distance_m / 2)
    approach_14_lon, approach_14_lat, _ = _GEOD.fwd(threshold_14.lon, threshold_14.lat, bearing + 180, 3000)
    approach_32_lon, approach_32_lat, _ = _GEOD.fwd(threshold_32.lon, threshold_32.lat, bearing, 3000)
    return RunwayGeometry(
        threshold_14=threshold_14, threshold_32=threshold_32,
        midpoint=GeoPoint(lat=mid_lat, lon=mid_lon),
        approach_14=GeoPoint(lat=approach_14_lat, lon=approach_14_lon),
        approach_32=GeoPoint(lat=approach_32_lat, lon=approach_32_lon),
        true_bearing_14_deg=143.85, source=_SOURCE, source_date="2026-04",
    )


def _components(wind: WindVector, bearing_deg: float) -> tuple[float, float]:
    angle = radians(bearing_deg)
    along = wind.east_m_s * sin(angle) + wind.north_m_s * cos(angle)
    cross = wind.east_m_s * cos(angle) - wind.north_m_s * sin(angle)
    return -along, cross


def calculate_wind_shear(query: WindShearQuery) -> WindShearResult:
    bearing = vebs_geometry().true_bearing_14_deg + (180 if query.runway_direction == "32" else 0)
    approach_head, approach_cross = _components(query.approach_wind, bearing)
    runway_head, runway_cross = _components(query.runway_wind, bearing)
    delta_head = runway_head - approach_head
    delta_vector = hypot(runway_head - approach_head, runway_cross - approach_cross)
    return WindShearResult(
        runway_direction=query.runway_direction,
        approach_headwind_m_s=approach_head, runway_headwind_m_s=runway_head,
        approach_crosswind_m_s=approach_cross, runway_crosswind_m_s=runway_cross,
        delta_headwind_m_s=delta_head, delta_vector_m_s=delta_vector,
        delta_vector_kt=delta_vector * 1.9438444924,
        threshold_exceeded=delta_vector >= 15,
        source_description=query.source_description,
    )
