"""Evaluate each uploaded WGS84 asset through the existing location engine."""

from shapely.geometry import LineString, Point, Polygon

from backend.app.schemas.analytics import AssetFeature, AssetTriageEntry, AssetTriageReport, AssetTriageRequest
from backend.app.schemas.location import (
    ETAStatus, EvidenceStatus, GeoPoint, GeometryType, LocationQuery,
    PointGeometry, PolygonGeometry, RouteGeometry,
)
from backend.app.services.location_intelligence import prepare_location_query


def _location_geometry(feature: AssetFeature) -> tuple[GeometryType, dict, GeoPoint]:
    raw = feature.geometry
    coordinates = raw.get("coordinates")
    if not isinstance(coordinates, list):
        raise ValueError("GeoJSON geometry must contain coordinates")
    kind = raw.get("type")
    if kind == "Point":
        if len(coordinates) != 2:
            raise ValueError("Point coordinates must be [longitude, latitude]")
        point = PointGeometry(longitude=coordinates[0], latitude=coordinates[1])
        return GeometryType.POINT, point.model_dump(), GeoPoint(lat=point.latitude, lon=point.longitude)
    if kind == "LineString":
        points = [PointGeometry(longitude=pair[0], latitude=pair[1]) for pair in coordinates if isinstance(pair, list) and len(pair) == 2]
        if len(points) != len(coordinates):
            raise ValueError("LineString coordinates must be [longitude, latitude] pairs")
        route = RouteGeometry(waypoints=points)
        line = LineString([(point.longitude, point.latitude) for point in points])
        if not line.is_valid or line.length == 0:
            raise ValueError("Asset route must be a valid nonzero-length line")
        center = line.centroid
        return GeometryType.ROUTE, route.model_dump(exclude_none=True), GeoPoint(lat=center.y, lon=center.x)
    if kind == "Polygon":
        if len(coordinates) != 1 or not isinstance(coordinates[0], list):
            raise ValueError("Only single-ring GeoJSON Polygons are supported")
        ring = coordinates[0]
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("GeoJSON Polygon exterior ring must be closed")
        points = [PointGeometry(longitude=pair[0], latitude=pair[1]) for pair in ring[:-1] if isinstance(pair, list) and len(pair) == 2]
        if len(points) != len(ring) - 1:
            raise ValueError("Polygon coordinates must be [longitude, latitude] pairs")
        polygon = Polygon([(point.longitude, point.latitude) for point in points])
        if not polygon.is_valid or polygon.area == 0:
            raise ValueError("Asset Polygon must be valid and have nonzero area")
        payload = PolygonGeometry(vertices=points)
        center = polygon.centroid
        return GeometryType.POLYGON, payload.model_dump(), GeoPoint(lat=center.y, lon=center.x)
    raise ValueError("Supported asset geometries are Point, LineString, and single-ring Polygon")


def triage_assets(request: AssetTriageRequest) -> AssetTriageReport:
    entries: list[AssetTriageEntry] = []
    seen: set[str] = set()
    for index, feature in enumerate(request.feature_collection.features, start=1):
        asset_id = str(feature.id) if feature.id is not None else f"asset-{index:03d}"
        if asset_id in seen:
            raise ValueError(f"Duplicate asset id: {asset_id}")
        seen.add(asset_id)
        name = feature.properties.get("name", asset_id)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Asset {asset_id} requires a nonempty name")
        geometry_type, geometry, centroid = _location_geometry(feature)
        query = LocationQuery(
            geometry_type=geometry_type, geometry=geometry,
            name=name, source_of_location=f"GEOJSON_ASSET:{asset_id}",
            issue_time=request.issue_time, horizon_minutes=request.horizon_minutes,
            forecast_mode=request.forecast_mode,
        )
        result = prepare_location_query(query)
        statuses = [impact.eta.status for impact in result.impacts]
        etas = [impact.eta.eta_minutes for impact in result.impacts if impact.eta.status == ETAStatus.COMPUTED]
        if ETAStatus.ARRIVED in statuses:
            eta_status = "ARRIVED"
            eta_minutes = None
        elif etas:
            eta_status = "COMPUTED"
            eta_minutes = min(eta for eta in etas if eta is not None)
        elif result.status == "NOT_COMPUTABLE" or ETAStatus.NOT_COMPUTABLE in statuses:
            eta_status = "NOT_COMPUTABLE"
            eta_minutes = None
        else:
            eta_status = "UNKNOWN"
            eta_minutes = None
        entries.append(AssetTriageEntry(
            asset_id=asset_id, name=name.strip(), centroid=centroid,
            geometry_type=geometry_type.value, eta_status=eta_status,
            eta_minutes=eta_minutes, result=result,
        ))
    order = {"ARRIVED": 0, "COMPUTED": 1, "UNKNOWN": 2, "NOT_COMPUTABLE": 3}
    entries.sort(key=lambda entry: (order[entry.eta_status], entry.eta_minutes if entry.eta_minutes is not None else float("inf"), entry.asset_id))
    computable = sum(entry.result.status == "COMPUTED" for entry in entries)
    return AssetTriageReport(
        issue_time=request.issue_time,
        status="COMPUTED" if computable == len(entries) else "NOT_COMPUTABLE" if computable == 0 else "PARTIAL",
        evidence_status=EvidenceStatus.LEARNED_FORECAST if request.forecast_mode == "LEARNED" else EvidenceStatus.SIMULATED,
        method="BATCH_LOCATION_QUERY_SPATIAL_INTERSECTION",
        assets=entries,
    )
