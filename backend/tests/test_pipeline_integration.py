"""Phase 4-6 integration checks across replay, baseline and location API."""

from datetime import timedelta

from fastapi.testclient import TestClient

from backend.main import app
from backend.app.services.baseline_forecast import get_baseline_forecast


client = TestClient(app)
ISSUE_TIME = get_baseline_forecast().issue_time


def _query(geometry_type: str, geometry: dict, issue_time=ISSUE_TIME):
    return client.post(
        "/api/v1/location/query",
        json={
            "geometry_type": geometry_type,
            "geometry": geometry,
            "issue_time": issue_time.isoformat(),
            "horizon_minutes": 60,
        },
    )


def test_replay_baseline_has_tracked_cells_and_forecast_geometry():
    response = client.get("/api/v1/replay/baseline")
    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == "SIMULATED"
    assert payload["current_cells"]
    assert [cell["lead_minutes"] for cell in payload["forecast_cells"]] == list(range(5, 65, 5))
    assert all(len(cell["polygon"]) >= 3 for cell in payload["forecast_cells"])


def test_sevir_replay_tracks_in_pixel_space_without_india_coordinates():
    response = client.get("/api/v1/replay/grid/analysis/12")
    assert response.status_code == 200
    payload = response.json()
    assert payload["georeferenced"] is False
    assert payload["field_units"] == "SEVIR_UINT8"
    assert payload["quality_control_status"] == "TEXTURE_SCREEN_NON_PHYSICAL"
    assert payload["cells"]
    assert all("centroid_x" in cell and "centroid_y" in cell for cell in payload["cells"])


def test_jaydev_point_returns_nested_computed_eta_and_timeline():
    response = _query("POINT", {"longitude": 85.8245, "latitude": 20.2961})
    assert response.status_code == 202
    payload = response.json()
    assert payload["evidence_status"] == "SIMULATED"
    assert payload["status"] == "COMPUTED"
    assert len(payload["impacts"]) == 12
    assert all(impact["evidence_status"] == "SIMULATED" for impact in payload["impacts"])
    assert all(impact["model_version"] is None for impact in payload["impacts"])
    assert all(impact["issue_time"] == payload["issue_time"] for impact in payload["impacts"])
    assert 25 < payload["impacts"][0]["eta"]["eta_minutes"] < 30
    assert payload["impacts"][0]["eta"]["method"] == "LINEAR_TRACK_INTERSECTION"
    assert any(impact["spatial_relation"] in {"INTERSECTS", "WITHIN"} for impact in payload["impacts"])


def test_clear_point_has_no_fabricated_eta():
    response = _query("POINT", {"longitude": 86.5, "latitude": 20.9})
    assert response.status_code == 202
    impacts = response.json()["impacts"]
    assert impacts
    assert all(impact["eta"]["status"] == "UNKNOWN" for impact in impacts)
    assert all(impact["eta"]["eta_minutes"] is None for impact in impacts)


def test_route_and_polygon_use_same_spatial_engine():
    route = _query("ROUTE", {"waypoints": [
        {"longitude": 85.78, "latitude": 20.2961},
        {"longitude": 85.86, "latitude": 20.2961},
    ]})
    polygon = _query("POLYGON", {"vertices": [
        {"longitude": 85.82, "latitude": 20.29},
        {"longitude": 85.83, "latitude": 20.29},
        {"longitude": 85.83, "latitude": 20.30},
        {"longitude": 85.82, "latitude": 20.30},
    ]})
    assert route.status_code == polygon.status_code == 202
    for response in (route, polygon):
        assert any(impact["spatial_relation"] in {"INTERSECTS", "WITHIN"} for impact in response.json()["impacts"])
        assert any(impact["eta"]["status"] == "COMPUTED" for impact in response.json()["impacts"])


def test_issue_time_mismatch_stays_gated():
    response = _query(
        "POINT", {"longitude": 85.8245, "latitude": 20.2961}, ISSUE_TIME + timedelta(minutes=5)
    )
    assert response.status_code == 202
    assert response.json()["status"] == "NOT_COMPUTABLE"
    assert response.json()["impacts"] == []
