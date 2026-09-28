from fastapi import APIRouter

from backend.app.schemas.model import ModelArtifact
from backend.app.services.model_registry import list_model_artifacts


router = APIRouter()


@router.get("", response_model=list[ModelArtifact])
def models() -> list[ModelArtifact]:
    return list_model_artifacts()
