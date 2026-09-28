"""
backend/location/intersection.py
=================================
Phase 2 — Geospatial Intersection Engine

Evaluates the spatial relationship between a convective-cell forecast track
and a LocationQuery geometry at each forecast time step.

Design principles (PRD §5.1, §5.4, §5.6):
  • Works entirely in projected (metric) coordinates via pyproj for accurate
    distance and buffer calculations.
  • Returns a structured IntersectionResult — never a bare boolean.
  • Zero fabricated values: if geometry or track data are absent/malformed
    the result carries INSUFFICIENT_DATA evidence, not a placeholder number.
  • Distance is great-circle calculated in metres, converted to km.
  • Intersection polygon footprint radius is parametric (default 5 km) and
    passed explicitly so callers control it — no magic constants buried here.

Dependencies: shapely ≥ 2.0, pyproj ≥ 3.0, numpy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import numpy as np

try:
    from pyproj import Geod
    from shapely.geometry import (
        LineString,
        MultiPolygon,
        Point,
        Polygon,
        shape,
    )
    from shapely.ops import transform
    import pyproj
    _HAS_SPATIAL_DEPS = True
except ImportError:
    _HAS_SPATIAL_DEPS = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class IntersectionStatus(str, Enum):
    """Outcome of a single (cell, timestep) intersection test."""
    INTERSECTS   = "INTERSECTS"     # hazard footprint overlaps query geometry
    WITHIN       = "WITHIN"         # query geometry is fully inside footprint
    APPROACHING  = "APPROACHING"    # on trajectory toward geometry (no overlap yet)
    RECEDING     = "RECEDING"       # moving away; no overlap expected in horizon
    NO_RELATION  = "NO_RELATION"    # no deterministic spatial relationship
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # geometry / track data missing


@dataclass(frozen=True)
class CellPosition:
    """
    A single forecast position of a convective cell at a given lead time.

    lon, lat : WGS84 decimal degrees
    lead_min : minutes from issue_time (T0)
    radius_km: effective hazard footprint radius in km (default 5 km)
    confidence: track confidence [0, 1] — used by ETA engine
    """
    lon:        float
    lat:        float
    lead_min:   int
    radius_km:  float = 5.0
    confidence: float = 1.0


@dataclass
class IntersectionResult:
    """
    Result of the spatial test for a single (cell, time-step) pair.

    is_intersecting : True iff the cell footprint overlaps the query geometry.
    status          : Categorical label (see IntersectionStatus).
    distance_km     : Great-circle distance from query centroid to nearest
                      footprint boundary in km.  0.0 when intersecting.
    approach_bearing: Bearing (°N clockwise) from footprint centre to query
                      centroid at this time step.  None if not APPROACHING.
    lead_min        : Lead time of this record.
    confidence      : Track confidence inherited from CellPosition.
    """
    is_intersecting:  bool
    status:           IntersectionStatus
    distance_km:      float
    lead_min:         int
    confidence:       float
    approach_bearing: Optional[float]   = None
    geom_valid:       bool              = True    # False ⇒ shapely error caught


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_wgs84_azimuthal_crs(lon: float, lat: float) -> "pyproj.CRS":
    """
    Return an azimuthal equidistant projection centred on (lon, lat).
    All distance calculations are done in this CRS to avoid geodetic errors.
    """
    return pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m"
    )


def _wgs84_point_to_metres(
    proj_crs: "pyproj.CRS",
    lon: float,
    lat: float,
) -> Tuple[float, float]:
    """Transform a WGS84 (lon, lat) to metres in *proj_crs*."""
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326", proj_crs, always_xy=True
    )
    return transformer.transform(lon, lat)


def _build_query_geometry_shapely(
    geometry_type: str,
    geometry_dict: dict,
    centre_crs: "pyproj.CRS",
    buffer_m: float = 0.0,
) -> Optional["Polygon"]:
    """
    Convert a LocationQuery.geometry dict into a Shapely geometry projected
    into *centre_crs* (azimuthal equidistant in metres).

    Returns None on failure.
    """
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326", centre_crs, always_xy=True
    )

    gtype = geometry_type.upper()

    try:
        if gtype == "POINT":
            x, y = transformer.transform(
                geometry_dict["longitude"], geometry_dict["latitude"]
            )
            geom = Point(x, y)
            if buffer_m > 0:
                geom = geom.buffer(buffer_m)
            return geom

        elif gtype == "POLYGON":
            vertices = geometry_dict["vertices"]
            coords = [
                transformer.transform(v["longitude"], v["latitude"])
                for v in vertices
            ]
            return Polygon(coords)

        elif gtype == "ROUTE":
            waypoints = geometry_dict["waypoints"]
            coords = [
                transformer.transform(w["longitude"], w["latitude"])
                for w in waypoints
            ]
            line = LineString(coords)
            if buffer_m > 0:
                return line.buffer(buffer_m)
            return line

        else:
            logger.warning("Unknown geometry_type: %s", geometry_type)
            return None

    except Exception as exc:
        logger.error("Failed to build query geometry: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cell_footprint(
    position: CellPosition,
    centre_crs: "pyproj.CRS",
) -> Optional["Polygon"]:
    """
    Return the hazard footprint of a cell at *position* as a circular Shapely
    polygon (buffer in metres) projected into *centre_crs*.

    Returns None if projection fails.
    """
    if not _HAS_SPATIAL_DEPS:
        logger.error("Shapely/pyproj not available; cannot compute footprint")
        return None

    try:
        transformer = pyproj.Transformer.from_crs(
            "EPSG:4326", centre_crs, always_xy=True
        )
        cx, cy = transformer.transform(position.lon, position.lat)
        radius_m = position.radius_km * 1_000.0
        return Point(cx, cy).buffer(radius_m)

    except Exception as exc:
        logger.error("Footprint computation failed for cell at (%s, %s): %s",
                     position.lon, position.lat, exc)
        return None


def compute_great_circle_distance_km(
    lon1: float, lat1: float,
    lon2: float, lat2: float,
) -> float:
    """
    Returns the WGS84 great-circle distance in kilometres between two points.
    Uses pyproj.Geod for geodetically accurate calculation.
    """
    if not _HAS_SPATIAL_DEPS:
        # Haversine fallback (less accurate but dependency-free)
        R = 6371.0
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
        return R * 2 * np.arcsin(np.sqrt(a))

    geod = Geod(ellps="WGS84")
    _, _, dist_m = geod.inv(lon1, lat1, lon2, lat2)
    return abs(dist_m) / 1_000.0


def intersect_cell_track_with_query(
    geometry_type: str,
    geometry_dict:  dict,
    cell_positions: Sequence[CellPosition],
    query_point_buffer_m: float = 0.0,
) -> List[IntersectionResult]:
    """
    Evaluate spatial intersection between a convective-cell forecast track
    and a user-supplied query geometry.

    Parameters
    ----------
    geometry_type        : "POINT" | "POLYGON" | "ROUTE"
    geometry_dict        : serialised PointGeometry / PolygonGeometry / RouteGeometry
    cell_positions       : ordered forecast positions (ascending lead_min)
    query_point_buffer_m : expand POINT geometry by this many metres
                           (e.g. 500 m for a pedestrian zone)

    Returns
    -------
    List[IntersectionResult], one entry per CellPosition, in the same order.

    Notes
    -----
    • All projections are done into an azimuthal equidistant CRS centred on
      the query geometry centroid so that distance and buffer calculations
      are metric-accurate without significant distortion over the 0–6 h
      forecast domain (~100–300 km from the query point).
    • We do NOT use straight-line distance / speed at any point.
    """
    if not _HAS_SPATIAL_DEPS:
        logger.critical(
            "Shapely or pyproj is not installed. "
            "Install with: pip install shapely pyproj"
        )
        return [
            IntersectionResult(
                is_intersecting=False,
                status=IntersectionStatus.INSUFFICIENT_DATA,
                distance_km=float("nan"),
                lead_min=p.lead_min,
                confidence=p.confidence,
                geom_valid=False,
            )
            for p in cell_positions
        ]

    if not cell_positions:
        return []

    # ---- build projection CRS centred on query geometry ------------------
    gtype = geometry_type.upper()
    try:
        if gtype == "POINT":
            centre_lon = geometry_dict["longitude"]
            centre_lat = geometry_dict["latitude"]
        elif gtype == "POLYGON":
            verts = geometry_dict["vertices"]
            centre_lon = np.mean([v["longitude"] for v in verts])
            centre_lat = np.mean([v["latitude"]  for v in verts])
        elif gtype == "ROUTE":
            wpts = geometry_dict["waypoints"]
            centre_lon = np.mean([w["longitude"] for w in wpts])
            centre_lat = np.mean([w["latitude"]  for w in wpts])
        else:
            logger.warning("Unknown geometry_type '%s'; returning NO_RELATION", geometry_type)
            return [
                IntersectionResult(
                    is_intersecting=False,
                    status=IntersectionStatus.NO_RELATION,
                    distance_km=float("nan"),
                    lead_min=p.lead_min,
                    confidence=p.confidence,
                    geom_valid=False,
                )
                for p in cell_positions
            ]
    except (KeyError, TypeError) as exc:
        logger.error("Malformed geometry_dict: %s", exc)
        return [
            IntersectionResult(
                is_intersecting=False,
                status=IntersectionStatus.INSUFFICIENT_DATA,
                distance_km=float("nan"),
                lead_min=p.lead_min,
                confidence=p.confidence,
                geom_valid=False,
            )
            for p in cell_positions
        ]

    centre_crs = _build_wgs84_azimuthal_crs(centre_lon, centre_lat)

    # ---- build query geometry in projection ------------------------------
    query_geom = _build_query_geometry_shapely(
        geometry_type, geometry_dict, centre_crs, buffer_m=query_point_buffer_m
    )
    if query_geom is None or query_geom.is_empty:
        return [
            IntersectionResult(
                is_intersecting=False,
                status=IntersectionStatus.INSUFFICIENT_DATA,
                distance_km=float("nan"),
                lead_min=p.lead_min,
                confidence=p.confidence,
                geom_valid=False,
            )
            for p in cell_positions
        ]

    results: List[IntersectionResult] = []

    for pos in cell_positions:
        footprint = compute_cell_footprint(pos, centre_crs)

        if footprint is None or footprint.is_empty or not footprint.is_valid:
            results.append(IntersectionResult(
                is_intersecting=False,
                status=IntersectionStatus.INSUFFICIENT_DATA,
                distance_km=float("nan"),
                lead_min=pos.lead_min,
                confidence=pos.confidence,
                geom_valid=False,
            ))
            continue

        try:
            intersects = footprint.intersects(query_geom)
            within     = query_geom.within(footprint)

            if within:
                status = IntersectionStatus.WITHIN
                dist_km = 0.0
            elif intersects:
                status  = IntersectionStatus.INTERSECTS
                dist_km = 0.0
            else:
                # Compute nearest boundary distance in metres → km
                dist_m = query_geom.distance(footprint)
                dist_km = dist_m / 1_000.0

                # Determine approach bearing using WGS84 geodesy
                bearing = _compute_approach_bearing(
                    cell_positions, pos, centre_lon, centre_lat
                )
                _status = _classify_approach_or_reced(
                    cell_positions, pos, query_geom, centre_crs
                )
                results.append(IntersectionResult(
                    is_intersecting=False,
                    status=_status,
                    distance_km=dist_km,
                    lead_min=pos.lead_min,
                    confidence=pos.confidence,
                    approach_bearing=bearing,
                ))
                continue

            results.append(IntersectionResult(
                is_intersecting=True,
                status=status,
                distance_km=dist_km,
                lead_min=pos.lead_min,
                confidence=pos.confidence,
            ))

        except Exception as exc:
            logger.error("Intersection test failed at lead=%d: %s", pos.lead_min, exc)
            results.append(IntersectionResult(
                is_intersecting=False,
                status=IntersectionStatus.INSUFFICIENT_DATA,
                distance_km=float("nan"),
                lead_min=pos.lead_min,
                confidence=pos.confidence,
                geom_valid=False,
            ))

    return results


# ---------------------------------------------------------------------------
# Internal direction helpers
# ---------------------------------------------------------------------------

def _compute_approach_bearing(
    all_positions: Sequence[CellPosition],
    current_pos:   CellPosition,
    query_lon:     float,
    query_lat:     float,
) -> Optional[float]:
    """
    Returns the bearing (degrees, clockwise from N) from the current cell
    centre toward the query geometry centroid.  None if not computable.
    """
    if not _HAS_SPATIAL_DEPS:
        return None
    try:
        geod = Geod(ellps="WGS84")
        fwd_az, _, _ = geod.inv(
            current_pos.lon, current_pos.lat,
            query_lon, query_lat
        )
        return float(fwd_az % 360)
    except Exception:
        return None


def _classify_approach_or_reced(
    all_positions: Sequence[CellPosition],
    current_pos:   CellPosition,
    query_geom,
    centre_crs: "pyproj.CRS",
) -> IntersectionStatus:
    """
    Classify whether the cell is approaching or receding from the query
    geometry by comparing distances across consecutive track positions.

    Falls back to NO_RELATION if there is only one position or distances
    cannot be computed.
    """
    if not _HAS_SPATIAL_DEPS:
        return IntersectionStatus.NO_RELATION

    # Find current index in track
    positions = list(all_positions)
    try:
        idx = next(i for i, p in enumerate(positions) if p.lead_min == current_pos.lead_min)
    except StopIteration:
        return IntersectionStatus.NO_RELATION

    # Need at least one neighbour to assess direction
    if idx == 0 or idx >= len(positions) - 1:
        return IntersectionStatus.NO_RELATION

    def _dist(pos: CellPosition) -> float:
        fp = compute_cell_footprint(pos, centre_crs)
        if fp is None:
            return float("inf")
        return query_geom.distance(fp)

    try:
        d_prev = _dist(positions[idx - 1])
        d_curr = _dist(current_pos)
        d_next = _dist(positions[idx + 1]) if idx + 1 < len(positions) else d_curr

        # Approaching: distance is decreasing over consecutive steps
        if d_next < d_curr and d_curr < d_prev:
            return IntersectionStatus.APPROACHING
        if d_next > d_curr:
            return IntersectionStatus.RECEDING
        # Approximately stable
        return IntersectionStatus.APPROACHING if d_curr < d_prev else IntersectionStatus.RECEDING

    except Exception:
        return IntersectionStatus.NO_RELATION
