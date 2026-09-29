from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)
ISSUE_TIME = "2026-06-18T12:00:00Z"


def _assets(*features):
    return {
        "feature_collection": {"type": "FeatureCollection", "features": list(features)},
        "issue_time": ISSUE_TIME,
        "forecast_mode": "BASELINE",
    }


def _point(asset_id, name, lon, lat):
    return {
        "type": "Feature", "id": asset_id, "properties": {"name": name},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def test_triage_ranks_from_nested_eta_and_retains_evidence():
    response = client.post("/api/v1/location/triage", json=_assets(
        _point("far", "Remote base", 86.3, 20.8),
        _point("jaydev", "Jaydev hospital", 85.8245, 20.2961),
    ))
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "COMPUTED"
    assert [entry["asset_id"] for entry in report["assets"]] == ["jaydev", "far"]
    first = report["assets"][0]
    assert first["eta_status"] == "COMPUTED"
    assert first["eta_minutes"] > 0
    assert first["result"]["evidence_status"] == "SIMULATED"
    assert first["result"]["impacts"][0]["eta"]["method"]
    assert first["result"]["impacts"][0]["source_ids"]


def test_triage_rejects_invalid_and_duplicate_geojson_assets():
    malformed = client.post("/api/v1/location/triage", json=_assets(
        _point("bad", "Out of range", 999, 20),
    ))
    assert malformed.status_code == 422
    duplicate = client.post("/api/v1/location/triage", json=_assets(
        _point("same", "A", 85.82, 20.29),
        _point("same", "B", 85.83, 20.30),
    ))
    assert duplicate.status_code == 422


def test_learned_triage_does_not_emit_spatial_eta(monkeypatch):
    from backend.app.schemas.location import EvidenceStatus, LocationQueryResult

    def gated(query):
        assert query.forecast_mode == "LEARNED"
        return LocationQueryResult(
            query_id=query.query_id, issue_time=query.issue_time,
            status="NOT_COMPUTABLE", evidence_status=EvidenceStatus.LEARNED_FORECAST,
            impacts=[], message="No WGS84 georeferencing.",
        )

    monkeypatch.setattr("backend.app.services.asset_triage.prepare_location_query", gated)
    payload = _assets(_point("jaydev", "Jaydev hospital", 85.8245, 20.2961))
    payload["forecast_mode"] = "LEARNED"
    response = client.post("/api/v1/location/triage", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_COMPUTABLE"
    assert response.json()["assets"][0]["eta_minutes"] is None


def test_triage_keeps_valid_eta_when_another_cell_is_not_computable(monkeypatch):
    from backend.app.schemas.location import ETAResult, ETAStatus
    from backend.app.services.location_intelligence import prepare_location_query

    def mixed(query):
        result = prepare_location_query(query)
        result.impacts[0].eta = ETAResult(
            status=ETAStatus.NOT_COMPUTABLE, method="INSUFFICIENT_TRACK",
            not_computable_reason="One cell lacks continuity.",
        )
        return result

    monkeypatch.setattr("backend.app.services.asset_triage.prepare_location_query", mixed)
    response = client.post("/api/v1/location/triage", json=_assets(
        _point("jaydev", "Jaydev hospital", 85.8245, 20.2961),
    ))
    assert response.status_code == 200
    asset = response.json()["assets"][0]
    assert asset["eta_status"] == "COMPUTED"
    assert asset["eta_minutes"] is not None


def test_isochrone_bands_are_real_nested_swept_polygons():
    response = client.get("/api/v1/replay/isochrones")
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "COMPUTED"
    assert report["evidence_status"] == "SIMULATED"
    assert [band["lead_minutes"] for band in report["bands"]] == [10, 20, 30]
    assert all(band["geometry"]["type"] in {"Polygon", "MultiPolygon"} for band in report["bands"])
    assert all(band["area_km2"] > 0 for band in report["bands"])
    assert all(band["source_ids"] for band in report["bands"])


def test_learned_isochrones_are_gated():
    report = client.get("/api/v1/replay/isochrones", params={"forecast_mode": "LEARNED"}).json()
    assert report["status"] == "NOT_COMPUTABLE"
    assert report["bands"] == []


def test_rapid_intensification_uses_adjacent_observed_frames_only():
    growing = client.get("/api/v1/replay/intensification", params={"frame_index": 2}).json()
    assert growing["status"] == "COMPUTED"
    assert growing["cells"][0]["tag"] == "RAPID_INTENSIFICATION"
    assert growing["cells"][0]["rate_dbz_per_hour"] == 10.0
    assert growing["cells"][0]["previous_frame_id"] == "obs-m060"
    issue = client.get("/api/v1/replay/intensification", params={"frame_index": 3}).json()
    assert issue["cells"][0]["rate_dbz_per_hour"] == 6.0
    assert issue["cells"][0]["tag"] is None
    first = client.get("/api/v1/replay/intensification", params={"frame_index": 0}).json()
    assert first["status"] == "NOT_COMPUTABLE"
    learned = client.get("/api/v1/replay/intensification", params={"frame_index": 2, "forecast_mode": "LEARNED"}).json()
    assert learned["status"] == "NOT_COMPUTABLE" and learned["cells"] == []


def test_imd_bridge_is_dormant_and_exposes_pipeline():
    response = client.get("/api/v1/replay/imd-bridge")
    assert response.status_code == 200
    bridge = response.json()
    assert bridge["state"] == "AWAITING_AUTHORIZATION"
    assert bridge["connected"] is False
    assert "NetCDF" in " ".join(bridge["pipeline_steps"])
    assert "HDF5" in " ".join(bridge["pipeline_steps"])
