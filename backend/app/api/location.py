from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.app.schemas.analytics import AssetTriageReport, AssetTriageRequest
from backend.app.schemas.location import LocationQuery, LocationQueryResult
from backend.app.services.asset_triage import triage_assets
from backend.app.services.location_intelligence import prepare_location_query

router = APIRouter()


@router.post("/query", response_model=LocationQueryResult, status_code=202)
def query_location_impact(query: LocationQuery) -> LocationQueryResult:
    return prepare_location_query(query)


@router.post("/triage", response_model=AssetTriageReport)
def triage_location_assets(request: AssetTriageRequest) -> AssetTriageReport:
    try:
        return triage_assets(request)
    except (ValidationError, ValueError, TypeError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
