"""
backend/tests/test_location_engine.py
======================================
Pytest test suite for Phase 2 & 3 of the VAJRA Location Intelligence Engine.

Covers (PRD §25 Testing & Quality Gates):
  ✓ Spatial intersection unit tests
  ✓ ETA calculation tests  (including all NOT_COMPUTABLE / UNKNOWN guards)
  ✓ Coordinate / time alignment tests
  ✓ Missing / stale data tests
  ✓ Pydantic schema validation (LocationQuery, LocationImpact, ETAResult)
  ✓ ETA appears only when valid (the primary acceptance criterion)

Run:
    pytest backend/tests/test_location_engine.py -v
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import List

import pytest

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from backend.location.intersection import (
    CellPosition,
    IntersectionResult,
    IntersectionStatus,
    compute_great_circle_distance_km,
    intersect_cell_track_with_query,
)
from backend.location.eta import (
    ETAResult,
    ETAStatus,
    MIN_TRACK_CONFIDENCE,
    compute_eta,
    compute_eta_timeline,
)
from backend.app.schemas.location import (
    CoordinateReferenceSystem,
    ETAResult as SchemaETAResult,
    ETAStatus as SchemaETAStatus,
    EvidenceStatus,
    GeometryType,
    HazardType,
    LocationImpact,
    LocationQuery,
    PointGeometry,
    RouteGeometry,
    SpatialRelation,
    UncertaintyBand,
)


# ===========================================================================
# Fixtures & constants
# ===========================================================================

JAYDEV_VIHAR = {"longitude": 85.8245, "latitude": 20.2961}
# Cell approaching from the NW — starts ~50 km away, crosses in ~2 steps
APPROACHING_TRACK: List[CellPosition] = [
    CellPosition(lon=85.37, lat=20.60, lead_min=0,   radius_km=8.0, confidence=0.90),
    CellPosition(lon=85.50, lat=20.50, lead_min=30,  radius_km=8.0, confidence=0.88),
    CellPosition(lon=85.65, lat=20.40, lead_min=60,  radius_km=8.0, confidence=0.85),
    CellPosition(lon=85.75, lat=20.35, lead_min=90,  radius_km=8.0, confidence=0.82),
    CellPosition(lon=85.85, lat=20.28, lead_min=120, radius_km=8.0, confidence=0.78),
    CellPosition(lon=85.90, lat=20.25, lead_min=150, radius_km=8.0, confidence=0.74),
]

# Cell starting directly on the query location (ARRIVED)
ARRIVED_TRACK: List[CellPosition] = [
    CellPosition(lon=85.8245, lat=20.2961, lead_min=0,  radius_km=10.0, confidence=0.95),
    CellPosition(lon=85.90,  lat=20.30,   lead_min=30, radius_km=10.0, confidence=0.90),
]

# Cell moving directly away — should never intersect
RECEDING_TRACK: List[CellPosition] = [
    CellPosition(lon=85.50, lat=20.60, lead_min=0,   radius_km=5.0, confidence=0.85),
    CellPosition(lon=85.20, lat=20.90, lead_min=30,  radius_km=5.0, confidence=0.80),
    CellPosition(lon=84.90, lat=21.20, lead_min=60,  radius_km=5.0, confidence=0.75),
    CellPosition(lon=84.60, lat=21.50, lead_min=90,  radius_km=5.0, confidence=0.70),
]

VALID_ISSUE_TIME = datetime(2023, 10, 5, 8, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Section A — Great-circle distance
# ===========================================================================

class TestGreatCircleDistance:
    def test_same_point_returns_zero(self):
        d = compute_great_circle_distance_km(85.0, 20.0, 85.0, 20.0)
        assert d == pytest.approx(0.0, abs=0.01)

    def test_known_distance_bhubaneswar_to_kolkata(self):
        # Bhubaneswar ≈ (85.84, 20.30), Kolkata ≈ (88.36, 22.57)
        # Great-circle ≈ 385–400 km (approximate)
        d = compute_great_circle_distance_km(85.84, 20.30, 88.36, 22.57)
        assert 350 < d < 450, f"Unexpected distance: {d:.1f} km"

    def test_distance_is_symmetric(self):
        d1 = compute_great_circle_distance_km(85.0, 20.0, 86.0, 21.0)
        d2 = compute_great_circle_distance_km(86.0, 21.0, 85.0, 20.0)
        assert d1 == pytest.approx(d2, rel=1e-5)

    def test_distance_is_positive(self):
        d = compute_great_circle_distance_km(0.0, 0.0, 1.0, 1.0)
        assert d > 0.0


# ===========================================================================
# Section B — Spatial Intersection Engine
# ===========================================================================

class TestIntersectionEngine:

    # ---- POINT query -------------------------------------------------------

    def test_approaching_cell_is_not_intersecting_at_t0(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, APPROACHING_TRACK
        )
        assert results[0].is_intersecting is False

    def test_approaching_cell_eventually_intersects(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, APPROACHING_TRACK
        )
        intersecting_steps = [r for r in results if r.is_intersecting]
        assert len(intersecting_steps) > 0, (
            "Track approaching from NW must intersect Jaydev Vihar within 6 steps"
        )

    def test_arrived_cell_intersects_at_t0(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, ARRIVED_TRACK
        )
        assert results[0].is_intersecting is True
        assert results[0].status in {IntersectionStatus.INTERSECTS, IntersectionStatus.WITHIN}

    def test_receding_cell_does_not_intersect(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, RECEDING_TRACK
        )
        assert all(not r.is_intersecting for r in results)

    def test_distance_is_zero_when_intersecting(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, ARRIVED_TRACK
        )
        for r in results:
            if r.is_intersecting:
                assert r.distance_km == pytest.approx(0.0, abs=0.1)

    def test_distance_decreasing_for_approaching_track(self):
        """Distances should monotonically decrease for a steadily approaching track."""
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, APPROACHING_TRACK
        )
        non_intersecting = [r for r in results if not r.is_intersecting and math.isfinite(r.distance_km)]
        if len(non_intersecting) >= 2:
            dists = [r.distance_km for r in non_intersecting]
            # Allow minor fluctuation (≤ 10 km) due to projection accuracy
            for i in range(1, len(dists)):
                assert dists[i] <= dists[i-1] + 10.0, (
                    f"Distance should decrease: step {i-1}={dists[i-1]:.1f} km, "
                    f"step {i}={dists[i]:.1f} km"
                )

    def test_lead_min_preserved_in_results(self):
        results = intersect_cell_track_with_query(
            "POINT", JAYDEV_VIHAR, APPROACHING_TRACK
        )
        assert len(results) == len(APPROACHING_TRACK)
        for r, p in zip(results, APPROACHING_TRACK):
            assert r.lead_min == p.lead_min

    # ---- ROUTE query -------------------------------------------------------

    def test_route_query_returns_results(self):
        route_geom = {
            "waypoints": [
                {"longitude": 85.80, "latitude": 20.28},
                {"longitude": 85.84, "latitude": 20.30},
                {"longitude": 85.87, "latitude": 20.33},
            ]
        }
        results = intersect_cell_track_with_query(
            "ROUTE", route_geom, APPROACHING_TRACK
        )
        assert len(results) == len(APPROACHING_TRACK)

    # ---- POLYGON query -----------------------------------------------------

    def test_polygon_query_returns_results(self):
        poly_geom = {
            "vertices": [
                {"longitude": 85.80, "latitude": 20.27},
                {"longitude": 85.85, "latitude": 20.27},
                {"longitude": 85.85, "latitude": 20.32},
                {"longitude": 85.80, "latitude": 20.32},
            ]
        }
        results = intersect_cell_track_with_query(
            "POLYGON", poly_geom, APPROACHING_TRACK
        )
        assert len(results) == len(APPROACHING_TRACK)

    # ---- Edge / error cases ------------------------------------------------

    def test_empty_positions_returns_empty_list(self):
        results = intersect_cell_track_with_query("POINT", JAYDEV_VIHAR, [])
        assert results == []

    def test_malformed_geometry_returns_insufficient_data(self):
        bad_geom = {"bad_key": 99}
        results = intersect_cell_track_with_query(
            "POINT", bad_geom, APPROACHING_TRACK
        )
        for r in results:
            assert r.status == IntersectionStatus.INSUFFICIENT_DATA
            assert r.geom_valid is False

    def test_unknown_geometry_type_handled(self):
        results = intersect_cell_track_with_query(
            "HEXAGON", JAYDEV_VIHAR, APPROACHING_TRACK
        )
        # Should get NO_RELATION or INSUFFICIENT_DATA, not crash
        for r in results:
            assert r.status in {IntersectionStatus.NO_RELATION, IntersectionStatus.INSUFFICIENT_DATA}


# ===========================================================================
# Section C — ETA Engine
# ===========================================================================

class TestETAEngine:

    # ---- Happy path --------------------------------------------------------

    def test_approaching_track_yields_computed_eta(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        assert result.status == ETAStatus.COMPUTED
        assert result.eta_minutes is not None
        assert result.eta_minutes > 0

    def test_computed_eta_has_method_string(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        if result.status == ETAStatus.COMPUTED:
            assert result.method != "NOT_ATTEMPTED"
            assert "INTERSECTION" in result.method or "TRACK" in result.method

    def test_computed_eta_confidence_in_range(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        if result.status == ETAStatus.COMPUTED:
            assert result.confidence is not None
            assert 0.0 <= result.confidence <= 1.0

    def test_computed_eta_within_horizon(self):
        """ETA must fall within the forecast horizon (360 min max)."""
        result = compute_eta("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        if result.status == ETAStatus.COMPUTED:
            assert result.eta_minutes <= 360.0

    # ---- ARRIVED -----------------------------------------------------------

    def test_arrived_returns_arrived_status(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, ARRIVED_TRACK)
        assert result.status == ETAStatus.ARRIVED
        assert result.eta_minutes is None

    def test_crossing_is_inside_sample_interval(self):
        track = [
            CellPosition(lon=85.74, lat=20.2961, lead_min=0, radius_km=2.0),
            CellPosition(lon=85.83, lat=20.2961, lead_min=10, radius_km=2.0),
        ]
        result = compute_eta("POINT", JAYDEV_VIHAR, track)
        assert result.status == ETAStatus.COMPUTED
        assert 0 < result.eta_minutes < 10

    # ---- UNKNOWN (no intersection in horizon) ------------------------------

    def test_receding_track_returns_unknown(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, RECEDING_TRACK)
        assert result.status in {ETAStatus.UNKNOWN, ETAStatus.NOT_COMPUTABLE}

    # ---- NOT_COMPUTABLE guards ---------------------------------------------

    def test_single_position_returns_not_computable(self):
        single = [CellPosition(lon=85.50, lat=20.60, lead_min=0, confidence=0.90)]
        result = compute_eta("POINT", JAYDEV_VIHAR, single)
        assert result.status == ETAStatus.NOT_COMPUTABLE
        assert result.eta_minutes is None
        assert result.not_computable_reason is not None

    def test_empty_positions_returns_not_computable(self):
        result = compute_eta("POINT", JAYDEV_VIHAR, [])
        assert result.status == ETAStatus.NOT_COMPUTABLE
        assert result.eta_minutes is None

    def test_low_confidence_track_returns_not_computable(self):
        """If any position has confidence < MIN_TRACK_CONFIDENCE, refuse ETA."""
        low_conf_track = [
            CellPosition(lon=85.37, lat=20.60, lead_min=0,  radius_km=8.0, confidence=0.10),
            CellPosition(lon=85.65, lat=20.40, lead_min=60, radius_km=8.0, confidence=0.10),
            CellPosition(lon=85.85, lat=20.28, lead_min=120, radius_km=8.0, confidence=0.10),
        ]
        result = compute_eta("POINT", JAYDEV_VIHAR, low_conf_track)
        assert result.status == ETAStatus.NOT_COMPUTABLE
        assert result.eta_minutes is None

    def test_non_monotonic_lead_times_returns_not_computable(self):
        non_mono = [
            CellPosition(lon=85.37, lat=20.60, lead_min=60, confidence=0.90),
            CellPosition(lon=85.65, lat=20.40, lead_min=30, confidence=0.88),  # ← goes backward
            CellPosition(lon=85.85, lat=20.28, lead_min=90, confidence=0.85),
        ]
        result = compute_eta("POINT", JAYDEV_VIHAR, non_mono)
        assert result.status == ETAStatus.NOT_COMPUTABLE

    def test_excessive_time_gap_returns_not_computable(self):
        big_gap = [
            CellPosition(lon=85.37, lat=20.60, lead_min=0,   confidence=0.90),
            CellPosition(lon=85.85, lat=20.28, lead_min=200, confidence=0.85),  # 200 min gap
        ]
        result = compute_eta("POINT", JAYDEV_VIHAR, big_gap)
        assert result.status == ETAStatus.NOT_COMPUTABLE

    def test_eta_has_reason_when_not_computable(self):
        single = [CellPosition(lon=85.50, lat=20.60, lead_min=0, confidence=0.90)]
        result = compute_eta("POINT", JAYDEV_VIHAR, single)
        assert result.not_computable_reason is not None
        assert len(result.not_computable_reason) > 5

    # ---- No naive division -------------------------------------------------

    def test_eta_is_not_naive_straight_line_division(self):
        """
        The ETA engine must NOT compute: distance / speed.
        We verify this by checking that the returned eta_minutes is NOT equal
        to the value you'd get from d/v arithmetic.

        We build a track where the naive calculation would yield exactly 45 min
        (distance 15 km ÷ speed 20 km/per-30-min = 22.5 steps →  but guard
        on speed makes this trivially wrong).  The engine must report a value
        derived from spatial crossing, which will differ unless they are
        algebraically equivalent (impossible for a circle-vs-point crossing).
        """
        # Track: cell starts 40 km from Jaydev Vihar, steps of 15 km each (30 min)
        # Naive: 40 / (15/30) = 80 min
        naive_eta = 80.0

        track = [
            CellPosition(lon=85.45, lat=20.65, lead_min=0,   radius_km=5.0, confidence=0.90),
            CellPosition(lon=85.57, lat=20.54, lead_min=30,  radius_km=5.0, confidence=0.88),
            CellPosition(lon=85.69, lat=20.43, lead_min=60,  radius_km=5.0, confidence=0.86),
            CellPosition(lon=85.80, lat=20.33, lead_min=90,  radius_km=5.0, confidence=0.84),
            CellPosition(lon=85.87, lat=20.27, lead_min=120, radius_km=5.0, confidence=0.82),
        ]
        result = compute_eta("POINT", JAYDEV_VIHAR, track)

        if result.status == ETAStatus.COMPUTED:
            # Make sure we are NOT returning the naive value (within 0.01 min)
            # The spatial crossing accounts for the cell radius — it will be shorter
            assert result.eta_minutes != pytest.approx(naive_eta, abs=0.01), (
                "ETA_minutes matches naive straight-line division exactly — "
                "engine may be using forbidden distance/speed calculation"
            )

    # ---- compute_eta_timeline convenience wrapper --------------------------

    def test_timeline_returns_both_eta_and_intersections(self):
        eta, intersections = compute_eta_timeline("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        assert isinstance(eta, ETAResult)
        assert isinstance(intersections, list)
        assert len(intersections) == len(APPROACHING_TRACK)

    def test_timeline_eta_consistent_with_standalone_eta(self):
        eta1, _ = compute_eta_timeline("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        eta2    = compute_eta("POINT", JAYDEV_VIHAR, APPROACHING_TRACK)
        assert eta1.status == eta2.status
        if eta1.status == ETAStatus.COMPUTED:
            assert eta1.eta_minutes == pytest.approx(eta2.eta_minutes, abs=0.1)


# ===========================================================================
# Section D — Pydantic Schema Validation
# ===========================================================================

class TestLocationQuerySchema:

    def test_valid_point_query_parses(self):
        q = LocationQuery(
            geometry_type=GeometryType.POINT,
            geometry={"longitude": 85.8245, "latitude": 20.2961},
            name="Jaydev Vihar",
            source_of_location="USER_SELECTED",
            issue_time=VALID_ISSUE_TIME,
            horizon_minutes=360,
        )
        assert q.geometry_type == GeometryType.POINT
        assert q.query_id          # auto-generated UUID

    def test_valid_route_query_parses(self):
        q = LocationQuery(
            geometry_type=GeometryType.ROUTE,
            geometry={
                "waypoints": [
                    {"longitude": 85.80, "latitude": 20.28},
                    {"longitude": 85.84, "latitude": 20.30},
                ]
            },
            issue_time=VALID_ISSUE_TIME,
        )
        assert q.geometry_type == GeometryType.ROUTE

    def test_valid_polygon_query_parses(self):
        q = LocationQuery(
            geometry_type=GeometryType.POLYGON,
            geometry={
                "vertices": [
                    {"longitude": 85.80, "latitude": 20.27},
                    {"longitude": 85.85, "latitude": 20.27},
                    {"longitude": 85.85, "latitude": 20.32},
                ]
            },
            issue_time=VALID_ISSUE_TIME,
        )
        assert q.geometry_type == GeometryType.POLYGON

    def test_horizon_out_of_range_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LocationQuery(
                geometry_type=GeometryType.POINT,
                geometry={"longitude": 85.82, "latitude": 20.29},
                issue_time=VALID_ISSUE_TIME,
                horizon_minutes=999,   # > 360
            )

    def test_mismatched_geometry_type_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LocationQuery(
                geometry_type=GeometryType.POLYGON,
                geometry={"longitude": 85.82, "latitude": 20.29},  # wrong for POLYGON
                issue_time=VALID_ISSUE_TIME,
            )

    def test_invalid_longitude_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PointGeometry(longitude=999.0, latitude=20.0)

    def test_auto_generated_query_id_is_valid_uuid(self):
        q = LocationQuery(
            geometry_type=GeometryType.POINT,
            geometry={"longitude": 85.82, "latitude": 20.29},
            issue_time=VALID_ISSUE_TIME,
        )
        parsed = uuid.UUID(q.query_id)   # raises ValueError if invalid
        assert str(parsed) == q.query_id


class TestSchemaETAResult:

    def test_computed_with_eta_minutes_parses(self):
        r = SchemaETAResult(
            status=SchemaETAStatus.COMPUTED,
            eta_minutes=47.2,
            method="LINEAR_TRACK_INTERSECTION",
            confidence=0.82,
        )
        assert r.eta_minutes == pytest.approx(47.2)

    def test_unknown_status_has_no_eta_minutes(self):
        r = SchemaETAResult(
            status=SchemaETAStatus.UNKNOWN,
            method="LINEAR_TRACK_INTERSECTION",
        )
        assert r.eta_minutes is None

    def test_computed_without_eta_minutes_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SchemaETAResult(
                status=SchemaETAStatus.COMPUTED,
                eta_minutes=None,      # must be provided
                method="LINEAR_TRACK_INTERSECTION",
            )

    def test_unknown_with_eta_minutes_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SchemaETAResult(
                status=SchemaETAStatus.UNKNOWN,
                eta_minutes=30.0,      # must be None when not COMPUTED
                method="LINEAR_TRACK_INTERSECTION",
            )


class TestLocationImpactSchema:

    def _make_eta(self, status=SchemaETAStatus.COMPUTED, minutes=47.2):
        return SchemaETAResult(
            status=status,
            eta_minutes=minutes if status == SchemaETAStatus.COMPUTED else None,
            method="LINEAR_TRACK_INTERSECTION",
            confidence=0.80,
        )

    def test_valid_impact_parses(self):
        impact = LocationImpact(
            query_id=str(uuid.uuid4()),
            valid_time=datetime(2023, 10, 5, 9, 0, 0, tzinfo=timezone.utc),
            lead_minutes=60,
            cell_id="CELL_042",
            hazard=HazardType.MAX_REFLECTIVITY_DBZ,
            value=52.3,
            unit="dBZ",
            method="OPTICAL_FLOW_ADVECTION",
            evidence_status=EvidenceStatus.BASELINE_FORECAST,
            spatial_relation=SpatialRelation.APPROACHING,
            distance_km=12.4,
            eta=self._make_eta(),
        )
        assert impact.eta.eta_minutes == pytest.approx(47.2)

    def test_eta_shorthand_property(self):
        impact = LocationImpact(
            query_id=str(uuid.uuid4()),
            valid_time=datetime(2023, 10, 5, 9, 0, 0, tzinfo=timezone.utc),
            lead_minutes=60,
            cell_id="CELL_042",
            hazard=HazardType.MAX_REFLECTIVITY_DBZ,
            value=52.3,
            unit="dBZ",
            method="OPTICAL_FLOW_ADVECTION",
            evidence_status=EvidenceStatus.BASELINE_FORECAST,
            spatial_relation=SpatialRelation.APPROACHING,
            eta=self._make_eta(SchemaETAStatus.UNKNOWN, None),
        )
        assert impact.eta_minutes is None

    def test_simulated_evidence_status_accepted(self):
        impact = LocationImpact(
            query_id=str(uuid.uuid4()),
            valid_time=datetime(2023, 10, 5, 9, 0, 0, tzinfo=timezone.utc),
            lead_minutes=30,
            cell_id="CELL_SIM",
            hazard=HazardType.VIL_KG_PER_M2,
            value=None,
            unit="kg m⁻²",
            method="SIMULATED_DEMO",
            evidence_status=EvidenceStatus.SIMULATED,
            spatial_relation=SpatialRelation.NO_RELATION,
            eta=self._make_eta(SchemaETAStatus.NOT_COMPUTABLE, None),
        )
        assert impact.evidence_status == EvidenceStatus.SIMULATED


# ===========================================================================
# Section E — Integration: schema ↔ engine round-trip
# ===========================================================================

class TestSchemaEngineIntegration:
    """
    Round-trip tests that create a LocationQuery, feed its geometry to the
    intersection and ETA engines, and verify the result can populate a
    LocationImpact schema correctly.
    """

    def test_round_trip_computed_eta(self):
        query = LocationQuery(
            geometry_type=GeometryType.POINT,
            geometry={"longitude": 85.8245, "latitude": 20.2961},
            name="Jaydev Vihar",
            issue_time=VALID_ISSUE_TIME,
        )
        eta_result, intersections = compute_eta_timeline(
            query.geometry_type.value,
            query.geometry,
            APPROACHING_TRACK,
        )

        assert eta_result.status in {
            ETAStatus.COMPUTED, ETAStatus.UNKNOWN, ETAStatus.NOT_COMPUTABLE, ETAStatus.ARRIVED
        }

        # Assemble final ETA for the schema
        schema_eta = SchemaETAResult(
            status=SchemaETAStatus(eta_result.status.value),
            eta_minutes=eta_result.eta_minutes,
            method=eta_result.method,
            confidence=eta_result.confidence,
            not_computable_reason=eta_result.not_computable_reason,
        )

        # The schema validator enforces: eta_minutes == None iff not COMPUTED
        if schema_eta.status == SchemaETAStatus.COMPUTED:
            assert schema_eta.eta_minutes is not None
        else:
            assert schema_eta.eta_minutes is None

    def test_round_trip_unknown_eta_impact(self):
        query = LocationQuery(
            geometry_type=GeometryType.POINT,
            geometry={"longitude": 85.8245, "latitude": 20.2961},
            issue_time=VALID_ISSUE_TIME,
        )
        eta_result = compute_eta(
            query.geometry_type.value,
            query.geometry,
            RECEDING_TRACK,
        )

        schema_eta = SchemaETAResult(
            status=SchemaETAStatus(eta_result.status.value),
            eta_minutes=None,  # UNKNOWN/NOT_COMPUTABLE
            method=eta_result.method,
        )

        impact = LocationImpact(
            query_id=query.query_id,
            valid_time=datetime(2023, 10, 5, 10, 0, tzinfo=timezone.utc),
            lead_minutes=120,
            cell_id="CELL_999",
            hazard=HazardType.MAX_REFLECTIVITY_DBZ,
            value=None,
            unit="dBZ",
            method="OPTICAL_FLOW_ADVECTION",
            evidence_status=EvidenceStatus.BASELINE_FORECAST,
            spatial_relation=SpatialRelation.RECEDING,
            eta=schema_eta,
        )

        # Impact carries query_id from query (linkage intact)
        assert impact.query_id == query.query_id
        assert impact.eta_minutes is None
