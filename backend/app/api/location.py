from fastapi import APIRouter

from backend.app.schemas.location import LocationQuery, LocationQueryResult
from backend.app.services.location_intelligence import prepare_location_query

router = APIRouter()


@router.post("/query", response_model=LocationQueryResult, status_code=202)
def query_location_impact(query: LocationQuery) -> LocationQueryResult:
    return prepare_location_query(query)
