"""Translate tracked baseline forecast cells into queryable location impacts."""

from collections import defaultdict
from math import isfinite

from backend.app.schemas.location import (
    CoordinateReferenceSystem,
    ETAResult,
    EvidenceStatus,
    HazardType,
    LocationImpact,
    LocationQuery,
    LocationQueryResult,
    SpatialRelation,
)
from backend.app.services.baseline_forecast import get_baseline_forecast
from backend.location.eta import compute_eta_timeline
from backend.location.intersection import CellPosition, IntersectionStatus


def prepare_location_query(query: LocationQuery) -> LocationQueryResult:
    if query.forecast_mode == "LEARNED":
        try:
            from backend.app.services.learned_forecast import get_learned_grid_forecast

            learned = get_learned_grid_forecast()
        except (ImportError, FileNotFoundError, ValueError, RuntimeError) as exc:
            return _not_computable(
                query, f"Learned model output is unavailable: {exc}",
                evidence_status=EvidenceStatus.LEARNED_FORECAST,
                model_version="convlstm-sevir-v0",
                model_status="UNVALIDATED_PROTOTYPE",
            )
        if not learned.georeferenced:
            return _not_computable(
                query,
                "Learned SEVIR VIL forecast has no georeferencing or India-compatible input; "
                "a WGS84 location intersection and Jaydev Vihar ETA are not computable.",
                evidence_status=EvidenceStatus.LEARNED_FORECAST,
                model_version=learned.model_version,
                model_status=learned.model_status,
            )

    baseline = get_baseline_forecast()
    if query.coordinate_reference_system != CoordinateReferenceSystem.WGS84:
        return _not_computable(query, "Only EPSG:4326 is supported by this baseline.")
    if query.issue_time != baseline.issue_time:
        return _not_computable(query, "Query issue_time must match the replay issue time.")

    current_by_id = {cell.cell_id: cell for cell in baseline.current_cells}
    tracks_by_id = {track.cell_id: track for track in baseline.tracks}
    forecasts_by_id = defaultdict(list)
    for forecast in baseline.forecast_cells:
        if forecast.lead_minutes <= min(query.horizon_minutes, 60):
            forecasts_by_id[forecast.cell_id].append(forecast)

    impacts: list[LocationImpact] = []
    for cell_id, forecasts in forecasts_by_id.items():
        current = current_by_id.get(cell_id)
        track = tracks_by_id.get(cell_id)
        if current is None or track is None:
            continue
        forecasts.sort(key=lambda item: item.lead_minutes)
        # Continuity score reflects scan count only; it is not calibrated weather skill.
        continuity = min(1.0, track.age_scans / 3.0)
        positions = [
            CellPosition(
                lon=current.centroid.lon,
                lat=current.centroid.lat,
                lead_min=0,
                radius_km=current.equivalent_radius_km,
                confidence=continuity,
            ),
            *[
                CellPosition(
                    lon=forecast.centroid.lon,
                    lat=forecast.centroid.lat,
                    lead_min=forecast.lead_minutes,
                    radius_km=forecast.equivalent_radius_km,
                    confidence=continuity,
                )
                for forecast in forecasts
            ],
        ]
        eta_result, intersections = compute_eta_timeline(
            query.geometry_type.value, query.geometry, positions
        )
        eta = ETAResult(
            status=eta_result.status.value,
            eta_minutes=eta_result.eta_minutes,
            method=eta_result.method,
            confidence=eta_result.confidence,
            not_computable_reason=eta_result.not_computable_reason,
        )
        for forecast, intersection in zip(forecasts, intersections[1:], strict=True):
            relation = (
                intersection.status.value
                if intersection.status != IntersectionStatus.INSUFFICIENT_DATA
                else SpatialRelation.NO_RELATION.value
            )
            impacts.append(
                LocationImpact(
                    query_id=query.query_id,
                    issue_time=baseline.issue_time,
                    valid_time=forecast.valid_time,
                    lead_minutes=forecast.lead_minutes,
                    cell_id=cell_id,
                    hazard=HazardType.MAX_REFLECTIVITY_DBZ,
                    value=forecast.max_reflectivity_dbz,
                    unit="dBZ",
                    method=forecast.method,
                    evidence_status=forecast.evidence_status,
                    source_ids=forecast.source_ids,
                    forecast_id=forecast.forecast_id,
                    model_version=forecast.model_version,
                    spatial_relation=relation,
                    distance_km=round(intersection.distance_km, 3)
                    if isfinite(intersection.distance_km) else None,
                    eta=eta,
                )
            )

    impacts.sort(key=lambda impact: (impact.lead_minutes, impact.cell_id))
    computed_etas = [
        impact.eta.eta_minutes for impact in impacts
        if impact.eta.eta_minutes is not None
    ]
    if computed_etas:
        first_eta = min(computed_etas)
        message = f"Simulated baseline footprint first intersects at T+{first_eta:.1f} min. Not operational weather guidance."
    elif any(impact.eta.status.value == "ARRIVED" for impact in impacts):
        message = "Simulated baseline footprint already intersects at issue time. Not operational weather guidance."
    else:
        message = "No computable simulated intersection within the forecast horizon. Not operational weather guidance."
    return LocationQueryResult(
        query_id=query.query_id,
        issue_time=baseline.issue_time,
        status="COMPUTED",
        evidence_status=baseline.evidence_status,
        impacts=impacts,
        message=message,
    )


def _not_computable(
    query: LocationQuery,
    message: str,
    *,
    evidence_status: EvidenceStatus = EvidenceStatus.SIMULATED,
    model_version: str | None = None,
    model_status: str | None = None,
) -> LocationQueryResult:
    return LocationQueryResult(
        query_id=query.query_id,
        issue_time=query.issue_time,
        status="NOT_COMPUTABLE",
        evidence_status=evidence_status,
        model_version=model_version,
        model_status=model_status,
        impacts=[],
        message=message,
    )
