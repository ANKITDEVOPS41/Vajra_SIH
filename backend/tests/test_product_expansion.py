from math import isclose

from fastapi.testclient import TestClient

from backend.app.schemas.airfield import WindShearQuery, WindVector
from backend.app.science.airfield import calculate_wind_shear, vebs_geometry
from backend.app.science.verification import ContingencyTable, categorical_scores
from backend.app.science.wmo_scorecard import build_wmo_scorecard
from backend.app.services.replay_verification import verify_synthetic_replay
from backend.main import app


client = TestClient(app)


def test_wmo_contingency_formulas():
    scores = categorical_scores(ContingencyTable(2, 1, 1, 6))
    assert scores.pod == 2 / 3
    assert scores.far == 1 / 3
    assert scores.csi == 0.5
    assert scores.heidke_skill_score == 11 / 21


def test_scorecard_keeps_unpaired_leads_unscored():
    card = build_wmo_scorecard(verify_synthetic_replay())
    assert [row.lead_minutes for row in card.leads] == [15, 30, 45, 60, 90, 120]
    assert [row.lead_minutes for row in card.leads if row.status == "COMPUTED"] == [30, 60]
    assert all(row.pod is None and row.hss is None for row in card.leads if row.status == "NOT_COMPUTABLE")
    assert card.forecast_validation_status == "UNVALIDATED"
    response = client.get("/api/v1/replay/wmo-scorecard")
    assert response.status_code == 200
    assert response.json()["source"] == "SYNTHETIC"


def test_vebs_geometry_uses_published_runway_and_three_km_gates():
    geometry = vebs_geometry()
    assert geometry.runway == "14/32"
    assert geometry.true_bearing_14_deg == 143.85
    assert 20.25 < geometry.threshold_14.lat < 20.27
    assert geometry.approach_14.lat > geometry.threshold_14.lat
    assert geometry.approach_32.lat < geometry.threshold_32.lat


def test_wind_shear_vector_math_and_threshold():
    query = WindShearQuery(
        runway_direction="14", approach_wind=WindVector(east_m_s=0, north_m_s=0),
        runway_wind=WindVector(east_m_s=15, north_m_s=0), source_description="Test vector",
    )
    result = calculate_wind_shear(query)
    assert isclose(result.delta_vector_m_s, 15)
    assert isclose(result.delta_vector_kt, 29.157667386, rel_tol=1e-8)
    assert result.threshold_exceeded
    assert result.status == "USER_SUPPLIED_CALCULATION"
    assert client.post("/api/v1/airfield/wind-shear", json=query.model_dump()).status_code == 200
    assert not calculate_wind_shear(query.model_copy(update={"runway_wind": WindVector(east_m_s=14.9, north_m_s=0)})).threshold_exceeded


def test_observed_radar_only_serves_actual_replay_frames():
    response = client.get("/api/v1/replay/observed-radar/30")
    assert response.status_code == 200
    data = response.json()
    assert data["evidence_status"] == "SIMULATED"
    assert data["width"] == data["height"] == 128
    assert max(max(row) for row in data["values"]) > 30
    assert client.get("/api/v1/replay/observed-radar/15").status_code == 404
