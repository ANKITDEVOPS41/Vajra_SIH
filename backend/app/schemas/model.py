from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelArtifact(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    architecture: str
    framework: str
    checkpoint_path: str
    checkpoint_sha256: str
    parameter_count: int
    status: Literal["UNVALIDATED_PROTOTYPE", "VALIDATED"]
    evidence_status: Literal["PROPOSED", "IMPLEMENTED", "VALIDATED"]
    training_dataset: str
    input_contract: str
    output_contract: str
    limitations: list[str]
