"""Cumulative swept WGS84 footprints derived from the active baseline polygons."""

from datetime import timedelta

from pyproj import CRS, Transformer
from shapely.geometry import Polygon, mapping
from shapely.ops import transform, unary_union

from backend.app.schemas.analytics import IsochroneBand, IsochroneReport
from backend.app.schemas.location import EvidenceStatus
from backend.app.services.baseline_forecast import get_baseline_forecast


def build_isochrones(forecast_mode: str = "BASELINE") -> IsochroneReport:
    if forecast_mode == "LEARNED":
        return IsochroneReport(
            status="NOT_COMPUTABLE", issue_time=None,
            evidence_status=EvidenceStatus.LEARNED_FORECAST,
            method="NOT_ATTEMPTED_UNGEOREFERENCED_MODEL", bands=[],
            message="SEVIR ConvLSTM cells have no WGS84 georeferencing; India isochrones are not computable.",
        )
    baseline = get_baseline_forecast()
    if not baseline.current_cells or baseline.evidence_status != EvidenceStatus.SIMULATED:
        return IsochroneReport(
            status="NOT_COMPUTABLE", issue_time=baseline.issue_time,
            evidence_status=baseline.evidence_status, method="NO_GEOREFERENCED_TRACKS",
            bands=[], message="No georeferenced current cell footprint is available.",
        )
    center_lat = sum(cell.centroid.lat for cell in baseline.current_cells) / len(baseline.current_cells)
    center_lon = sum(cell.centroid.lon for cell in baseline.current_cells) / len(baseline.current_cells)
    metric = CRS.from_proj4(f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +datum=WGS84 +units=m +no_defs")
    to_metric = Transformer.from_crs("EPSG:4326", metric, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(metric, "EPSG:4326", always_xy=True).transform
    forecast_by_id = {
        cell.cell_id: sorted(
            (forecast for forecast in baseline.forecast_cells if forecast.cell_id == cell.cell_id),
            key=lambda forecast: forecast.lead_minutes,
        )
        for cell in baseline.current_cells
    }
    if any(not forecasts or forecasts[-1].lead_minutes < 30 for forecasts in forecast_by_id.values()):
        return IsochroneReport(
            status="NOT_COMPUTABLE", issue_time=baseline.issue_time,
            evidence_status=baseline.evidence_status, method="INCOMPLETE_FORECAST_TRACK",
            bands=[], message="A continuous WGS84 forecast track through T+30 is required.",
        )

    previous_envelope = unary_union([
        transform(to_metric, Polygon([(point.lon, point.lat) for point in cell.polygon]))
        for cell in baseline.current_cells
    ])
    bands: list[IsochroneBand] = []
    for lead in (10, 20, 30):
        sweeps = []
        included = []
        for cell in baseline.current_cells:
            previous = transform(to_metric, Polygon([(point.lon, point.lat) for point in cell.polygon]))
            sweeps.append(previous)
            for forecast in forecast_by_id[cell.cell_id]:
                if forecast.lead_minutes > lead:
                    break
                current = transform(to_metric, Polygon([(point.lon, point.lat) for point in forecast.polygon]))
                sweeps.append(unary_union((previous, current)).convex_hull)
                previous = current
                included.append(forecast)
        envelope = unary_union(sweeps)
        band = envelope.difference(previous_envelope)
        if band.is_empty or band.area <= 0:
            return IsochroneReport(
                status="NOT_COMPUTABLE", issue_time=baseline.issue_time,
                evidence_status=baseline.evidence_status, method="NO_NEW_SWEPT_AREA",
                bands=[], message="The track does not add a swept footprint at every requested lead.",
            )
        bands.append(IsochroneBand(
            lead_minutes=lead,
            valid_time=baseline.issue_time + timedelta(minutes=lead),
            area_km2=round(band.area / 1_000_000, 3),
            geometry=mapping(transform(to_wgs84, band)),
            method="WGS84_BASELINE_POLYGON_SWEPT_UNION_DIFFERENCE",
            evidence_status=baseline.evidence_status,
            source_ids=sorted({source for forecast in included for source in forecast.source_ids}),
            forecast_ids=[forecast.forecast_id for forecast in included],
        ))
        previous_envelope = envelope
    return IsochroneReport(
        status="COMPUTED", issue_time=baseline.issue_time,
        evidence_status=baseline.evidence_status,
        method="WGS84_BASELINE_POLYGON_SWEPT_UNION_DIFFERENCE",
        bands=bands,
        message="Incremental T+10/20/30 swept footprints from simulated constant-velocity forecast polygons; not a probability or operational warning.",
    )
