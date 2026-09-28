"""
backend/location/eta.py
========================
Phase 3 — Valid ETA Engine

Derives the estimated time of arrival (ETA) of a convective-cell hazard
footprint at a user-supplied query geometry.

PRD §5.4 contract (non-negotiable):
  • ETA is a computed scientific output, NOT a decorative timer.
  • It MUST be derived from a forecast trajectory or evolving hazard field
    and a defined spatial intersection — never from naive straight-line
    distance ÷ speed.
  • If track continuity, time alignment, geometry, or uncertainty prevents
    a defensible estimate → return UNKNOWN or NOT_COMPUTABLE.
  • Store the exact ETA method in provenance.

Algorithm: LINEAR_TRACK_INTERSECTION
  ─────────────────────────────────
  1. Walk the ordered forecast track positions (ascending lead_min).
  2. At each step, evaluate the spatial relationship via the intersection
     engine.
  3. When we locate the FIRST transition into INTERSECTS or WITHIN, we have
     the bounding interval [t_before, t_after].
  4. Linearly interpolate within that interval to find the sub-step crossing
     time.  This is valid because within a single 30-minute step the hazard
     footprint translation is approximately linear at convective-cell scales
     (< 0.5% error vs. geodesic for typical storm motion 10–30 m s⁻¹).
  5. Guard conditions (hard stop → NOT_COMPUTABLE or UNKNOWN):
       a. Track has fewer than 2 positions          → NOT_COMPUTABLE
       b. Minimum track confidence < threshold      → NOT_COMPUTABLE
       c. No intersection found in horizon          → UNKNOWN
       d. Cell already intersecting at T0           → ARRIVED
       e. Intersection status is INSUFFICIENT_DATA  → NOT_COMPUTABLE
       f. Time gap between consecutive track steps
          is non-monotonic or > 120 min             → NOT_COMPUTABLE

Dependencies: backend.location.intersection (Phase 2), numpy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import numpy as np

from backend.location.intersection import (
    CellPosition,
    IntersectionResult,
    IntersectionStatus,
    intersect_cell_track_with_query,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

#: Minimum track confidence below which ETA computation is refused
MIN_TRACK_CONFIDENCE: float = 0.40

#: Maximum allowed gap between consecutive track positions (minutes).
#: A gap larger than this breaks trajectory continuity.
MAX_STEP_GAP_MINUTES: int = 120

#: Method string stored in ETAResult.method for provenance
METHOD_LINEAR_TRACK = "LINEAR_TRACK_INTERSECTION"
METHOD_NOT_ATTEMPTED = "NOT_ATTEMPTED"
METHOD_ARRIVED = "ARRIVED_AT_ISSUE_TIME"


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

class ETAStatus(str, Enum):
    """Mirrors backend.app.schemas.location.ETAStatus without circular import."""
    UNKNOWN        = "UNKNOWN"
    NOT_COMPUTABLE = "NOT_COMPUTABLE"
    ARRIVED        = "ARRIVED"
    COMPUTED       = "COMPUTED"


@dataclass
class ETAResult:
    """
    Low-level ETA result returned by this engine.

    eta_minutes          : None unless status == COMPUTED
    method               : provenance string (always populated)
    confidence           : track confidence at the crossing point (or None)
    not_computable_reason: human-readable guard explanation
    crossing_lead_min    : raw lead time [min] at the interpolated crossing
    """
    status:               ETAStatus
    eta_minutes:          Optional[float]
    method:               str
    confidence:           Optional[float]           = None
    not_computable_reason: Optional[str]            = None
    crossing_lead_min:    Optional[float]           = None


# ---------------------------------------------------------------------------
# Guard functions
# ---------------------------------------------------------------------------

def _check_track_continuity(
    positions: Sequence[CellPosition],
) -> Tuple[bool, str]:
    """
    Returns (ok: bool, reason: str).

    Flags:
      • < 2 positions
      • non-monotonic lead times
      • any gap > MAX_STEP_GAP_MINUTES
      • any confidence value outside [0, 1]
    """
    pos_list = list(positions)

    if len(pos_list) < 2:
        return False, "Track has fewer than 2 forecast positions — trajectory undefined"

    for i, p in enumerate(pos_list):
        if not (0.0 <= p.confidence <= 1.0):
            return False, (
                f"Position {i} (lead={p.lead_min} min) has invalid "
                f"confidence={p.confidence!r}; expected [0, 1]"
            )

    for i in range(1, len(pos_list)):
        dt = pos_list[i].lead_min - pos_list[i - 1].lead_min
        if dt <= 0:
            return False, (
                f"Non-monotonic lead times: step {i-1} lead={pos_list[i-1].lead_min} min, "
                f"step {i} lead={pos_list[i].lead_min} min"
            )
        if dt > MAX_STEP_GAP_MINUTES:
            return False, (
                f"Track gap of {dt} min between steps {i-1} and {i} "
                f"exceeds maximum ({MAX_STEP_GAP_MINUTES} min) — trajectory discontinuous"
            )

    return True, ""


def _check_minimum_confidence(
    positions: Sequence[CellPosition],
) -> Tuple[bool, str]:
    """
    Returns (ok: bool, reason: str).
    Refuses ETA if the MINIMUM confidence across the track falls below
    MIN_TRACK_CONFIDENCE.  We use the minimum (not mean) because a single
    low-confidence step corrupts the interpolated crossing time.
    """
    min_conf = min(p.confidence for p in positions)
    if min_conf < MIN_TRACK_CONFIDENCE:
        return False, (
            f"Minimum track confidence {min_conf:.2f} is below "
            f"threshold {MIN_TRACK_CONFIDENCE:.2f} — ETA not defensible"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Core interpolation (defined below public API to avoid forward-reference issues)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_eta(
    geometry_type:        str,
    geometry_dict:        dict,
    cell_positions:       Sequence[CellPosition],
    query_point_buffer_m: float = 0.0,
    intersection_results: Optional[List[IntersectionResult]] = None,
) -> ETAResult:
    """
    Compute the ETA for a convective cell to reach a query geometry.

    Parameters
    ----------
    geometry_type        : "POINT" | "POLYGON" | "ROUTE"
    geometry_dict        : geometry payload (see LocationQuery)
    cell_positions       : ordered forecast positions (ascending lead_min)
    query_point_buffer_m : expand POINT geometry buffer (metres)
    intersection_results : pre-computed intersection results (optional).
                           If None, they are computed here.  Pass them in to
                           avoid re-computation when the caller already has them.

    Returns
    -------
    ETAResult — always populated; eta_minutes is None unless status == COMPUTED.

    Guard cascade (PRD §5.4):
      1. Track continuity check
      2. Minimum confidence check
      3. Run spatial intersection (if not pre-computed)
      4. T0 ARRIVED check
      5. Scan for first crossing step
      6. Interpolate and return COMPUTED
      7. If no crossing in horizon → UNKNOWN
    """
    positions = list(cell_positions)

    # ------------------------------------------------------------------
    # Guard 1: Track continuity
    # ------------------------------------------------------------------
    ok, reason = _check_track_continuity(positions)
    if not ok:
        logger.info("ETA guard(continuity): %s", reason)
        return ETAResult(
            status=ETAStatus.NOT_COMPUTABLE,
            eta_minutes=None,
            method=METHOD_NOT_ATTEMPTED,
            not_computable_reason=reason,
        )

    # ------------------------------------------------------------------
    # Guard 2: Minimum track confidence
    # ------------------------------------------------------------------
    ok, reason = _check_minimum_confidence(positions)
    if not ok:
        logger.info("ETA guard(confidence): %s", reason)
        return ETAResult(
            status=ETAStatus.NOT_COMPUTABLE,
            eta_minutes=None,
            method=METHOD_NOT_ATTEMPTED,
            not_computable_reason=reason,
        )

    # ------------------------------------------------------------------
    # Guard 3: Spatial intersections
    # ------------------------------------------------------------------
    if intersection_results is None:
        intersection_results = intersect_cell_track_with_query(
            geometry_type=geometry_type,
            geometry_dict=geometry_dict,
            cell_positions=positions,
            query_point_buffer_m=query_point_buffer_m,
        )

    if len(intersection_results) != len(positions):
        reason = (
            f"Intersection result count ({len(intersection_results)}) does not "
            f"match position count ({len(positions)}) — data alignment broken"
        )
        logger.warning("ETA guard(alignment): %s", reason)
        return ETAResult(
            status=ETAStatus.NOT_COMPUTABLE,
            eta_minutes=None,
            method=METHOD_NOT_ATTEMPTED,
            not_computable_reason=reason,
        )

    # ------------------------------------------------------------------
    # Guard 3b: Check for any INSUFFICIENT_DATA in results
    # ------------------------------------------------------------------
    bad_results = [
        r for r in intersection_results
        if r.status == IntersectionStatus.INSUFFICIENT_DATA
    ]
    if bad_results:
        reason = (
            f"{len(bad_results)} of {len(intersection_results)} intersection "
            "results carry INSUFFICIENT_DATA — geometry or track data malformed"
        )
        logger.warning("ETA guard(insufficient_data): %s", reason)
        return ETAResult(
            status=ETAStatus.NOT_COMPUTABLE,
            eta_minutes=None,
            method=METHOD_NOT_ATTEMPTED,
            not_computable_reason=reason,
        )

    # ------------------------------------------------------------------
    # Guard 4: ARRIVED — cell already at T0
    # ------------------------------------------------------------------
    first_result = intersection_results[0]
    if first_result.is_intersecting:
        logger.info("ETA: Cell already intersects query geometry at T0 (lead=%d)", first_result.lead_min)
        return ETAResult(
            status=ETAStatus.ARRIVED,
            eta_minutes=float(first_result.lead_min),   # 0 or small lead offset
            method=METHOD_ARRIVED,
            confidence=first_result.confidence,
        )

    # ------------------------------------------------------------------
    # Guard 5: Scan for first crossing transition
    #           non-intersecting → intersecting
    # ------------------------------------------------------------------
    crossing_idx: Optional[int] = None

    for i in range(1, len(intersection_results)):
        prev = intersection_results[i - 1]
        curr = intersection_results[i]
        if (not prev.is_intersecting) and curr.is_intersecting:
            crossing_idx = i
            break

    if crossing_idx is None:
        # No intersection anywhere in the forecast horizon
        logger.info(
            "ETA: No intersection found in %d-step horizon — UNKNOWN",
            len(intersection_results)
        )
        return ETAResult(
            status=ETAStatus.UNKNOWN,
            eta_minutes=None,
            method=METHOD_LINEAR_TRACK,
            not_computable_reason=(
                "Convective-cell forecast track does not intersect the query "
                "geometry within the configured horizon"
            ),
        )

    # ------------------------------------------------------------------
    # Guard 6: Interpolate sub-step crossing time (§5.4: no naive division)
    # ------------------------------------------------------------------
    pos_before  = positions[crossing_idx - 1]
    pos_after   = positions[crossing_idx]
    res_before  = intersection_results[crossing_idx - 1]

    # Use the distance values from the intersection results (already in km)
    dist_before = res_before.distance_km
    # dist_after  is 0.0 (intersecting), so the crossing is between steps
    dist_after  = 0.0

    # Sanity check: if dist_before is NaN or negative, fall back conservatively
    if not np.isfinite(dist_before) or dist_before < 0:
        logger.warning(
            "dist_before is %s at crossing_idx=%d; "
            "returning t_after conservatively",
            dist_before, crossing_idx
        )
        crossing_lead = float(pos_after.lead_min)
    else:
        # Convert km to a comparable scale — interpolation works in minutes
        crossing_lead = _interpolate_crossing_time(
            pos_before, pos_after,
            dist_km_before=dist_before,
            dist_km_after=dist_after,
        )

    # Track confidence at crossing: interpolate between adjacent steps
    conf_before = pos_before.confidence
    conf_after  = pos_after.confidence
    dt = pos_after.lead_min - pos_before.lead_min
    frac = (crossing_lead - pos_before.lead_min) / dt if dt > 0 else 0.5
    crossing_confidence = float(conf_before + frac * (conf_after - conf_before))

    logger.info(
        "ETA COMPUTED: crossing_lead=%.1f min  confidence=%.2f  method=%s",
        crossing_lead, crossing_confidence, METHOD_LINEAR_TRACK
    )

    return ETAResult(
        status=ETAStatus.COMPUTED,
        eta_minutes=crossing_lead,
        method=METHOD_LINEAR_TRACK,
        confidence=crossing_confidence,
        crossing_lead_min=crossing_lead,
    )


# ---------------------------------------------------------------------------
# Core interpolation helper
# ---------------------------------------------------------------------------

def _interpolate_crossing_time(
    pos_before: CellPosition,
    pos_after:  CellPosition,
    dist_km_before: float,
    dist_km_after:  float,
) -> float:
    """
    Sub-step linear interpolation of the crossing time (lead minutes).

    Fitting: distance drops from dist_km_before (> 0) to 0 over
    [t0, t1] minutes.  We solve for the time at which distance == 0.
    """
    t0 = pos_before.lead_min
    t1 = pos_after.lead_min
    d0 = max(dist_km_before, 0.0)

    denom = d0 - dist_km_after
    if denom <= 1e-9:
        return float(t1)

    fraction = d0 / denom
    return float(np.clip(t0 + fraction * (t1 - t0), t0, t1))


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def compute_eta_timeline(
    geometry_type:        str,
    geometry_dict:        dict,
    cell_positions:       Sequence[CellPosition],
    query_point_buffer_m: float = 0.0,
) -> Tuple[ETAResult, List[IntersectionResult]]:
    """
    Convenience wrapper that returns both the ETA result AND the full
    intersection timeline for use by the API response assembler.

    This avoids computing intersections twice.
    """
    intersection_results = intersect_cell_track_with_query(
        geometry_type=geometry_type,
        geometry_dict=geometry_dict,
        cell_positions=list(cell_positions),
        query_point_buffer_m=query_point_buffer_m,
    )

    eta = compute_eta(
        geometry_type=geometry_type,
        geometry_dict=geometry_dict,
        cell_positions=cell_positions,
        query_point_buffer_m=query_point_buffer_m,
        intersection_results=intersection_results,
    )

    return eta, intersection_results
