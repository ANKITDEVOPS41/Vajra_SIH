from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.location import EvidenceStatus


class GridReplayMetadata(BaseModel):
    event_id: str
    sample_id: str
    label: str
    mode: Literal["REPLAY"]
    evidence_status: EvidenceStatus
    dataset_id: str
    coverage: str
    field: str
    units: str
    frame_count: int
    time_step_minutes: int
    issue_index: int
    georeferenced: bool
    limitations: list[str]


class GridReplayFrame(BaseModel):
    event_id: str
    sample_id: str
    frame_index: int = Field(..., ge=0)
    offset_minutes: int
    evidence_status: EvidenceStatus
    field: str
    units: str
    georeferenced: bool
    width: int
    height: int
    values: list[list[int]]


class LearnedGridCell(BaseModel):
    cell_id: str
    centroid_x: float = Field(ge=0)
    centroid_y: float = Field(ge=0)
    area_pixels: int = Field(gt=0)
    radius_pixels: float = Field(gt=0)
    peak_normalized: float = Field(ge=0, le=1)


class LearnedGridFrame(BaseModel):
    lead_minutes: int = Field(ge=5, le=60)
    frame_index: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    values: list[list[int]]
    cells: list[LearnedGridCell]


class LearnedGridForecast(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    event_id: str
    sample_id: str
    issue_frame_index: int
    issue_time: None = None
    georeferenced: Literal[False]
    evidence_status: EvidenceStatus
    model_version: str
    model_status: Literal["UNVALIDATED_PROTOTYPE"]
    checkpoint_sha256: str
    method: Literal["LIGHTWEIGHT_CONVLSTM_SEVIR_VIL"]
    source_ids: list[str]
    units: Literal["NORMALIZED_SEVIR_VIL"]
    detection_threshold_normalized: float
    input_shape: list[int]
    output_shape: list[int]
    frames: list[LearnedGridFrame]
    limitations: list[str]
