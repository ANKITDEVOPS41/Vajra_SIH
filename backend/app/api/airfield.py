from fastapi import APIRouter

from backend.app.schemas.airfield import RunwayGeometry, WindShearQuery, WindShearResult
from backend.app.science.airfield import calculate_wind_shear, vebs_geometry

router = APIRouter()


@router.get("/vebs", response_model=RunwayGeometry)
def vebs() -> RunwayGeometry:
    return vebs_geometry()


@router.post("/wind-shear", response_model=WindShearResult)
def wind_shear(query: WindShearQuery) -> WindShearResult:
    return calculate_wind_shear(query)
