import json
from functools import lru_cache
from pathlib import Path

from backend.app.schemas.model import ModelArtifact


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_MANIFEST_DIR = PROJECT_ROOT / "models" / "prototype"


@lru_cache(maxsize=1)
def list_model_artifacts() -> list[ModelArtifact]:
    artifacts: list[ModelArtifact] = []
    for path in sorted(MODEL_MANIFEST_DIR.glob("*.json")):
        artifacts.append(ModelArtifact.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return artifacts


def get_model_artifact(model_id: str) -> ModelArtifact:
    for artifact in list_model_artifacts():
        if artifact.model_id == model_id:
            return artifact
    raise KeyError(f"Model artifact '{model_id}' is not registered.")
