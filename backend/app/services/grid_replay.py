from functools import lru_cache
from pathlib import Path

import h5py

from backend.app.schemas.location import EvidenceStatus
from backend.app.schemas.replay_grid import GridReplayFrame, GridReplayMetadata


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVENT_ID = "sevir-r17062923508259"
REPLAY_PATH = PROJECT_ROOT / "data" / "replay" / f"{EVENT_ID}.h5"
ISSUE_INDEX = 12


@lru_cache(maxsize=1)
def grid_replay_metadata() -> GridReplayMetadata:
    with h5py.File(REPLAY_PATH, "r") as handle:
        sample_id = handle["id"][0].decode("ascii")
        frame_count = int(handle["vil"].shape[-1])
    return GridReplayMetadata(
        event_id=EVENT_ID,
        sample_id=sample_id,
        label="SEVIR VIL event replay",
        mode="REPLAY",
        evidence_status=EvidenceStatus.DATASET_VERIFIED,
        dataset_id="sevir",
        coverage="United States",
        field="VIL",
        units="SEVIR_UINT8",
        frame_count=frame_count,
        time_step_minutes=5,
        issue_index=ISSUE_INDEX,
        georeferenced=False,
        limitations=[
            "The supplied subset does not include georeferencing metadata.",
            "This United States benchmark cannot support India performance claims.",
            "The field is observed VIL data, not a VAJRA forecast.",
        ],
    )


def load_grid_replay_frame(frame_index: int, downsample: int = 4) -> GridReplayFrame:
    metadata = grid_replay_metadata()
    if frame_index < 0 or frame_index >= metadata.frame_count:
        raise IndexError(f"Frame index must be between 0 and {metadata.frame_count - 1}.")
    grid = load_grid_replay_values(frame_index, downsample=downsample)
    return GridReplayFrame(
        event_id=metadata.event_id,
        sample_id=metadata.sample_id,
        frame_index=frame_index,
        offset_minutes=(frame_index - metadata.issue_index) * metadata.time_step_minutes,
        evidence_status=metadata.evidence_status,
        field=metadata.field,
        units=metadata.units,
        georeferenced=False,
        width=int(grid.shape[1]),
        height=int(grid.shape[0]),
        values=grid.astype(int).tolist(),
    )


def load_grid_replay_values(frame_index: int, downsample: int = 4):
    """Load raw SEVIR VIL values for analysis without assigning map coordinates."""
    metadata = grid_replay_metadata()
    if frame_index < 0 or frame_index >= metadata.frame_count:
        raise IndexError(f"Frame index must be between 0 and {metadata.frame_count - 1}.")
    with h5py.File(REPLAY_PATH, "r") as handle:
        return handle["vil"][0, ::downsample, ::downsample, frame_index]
