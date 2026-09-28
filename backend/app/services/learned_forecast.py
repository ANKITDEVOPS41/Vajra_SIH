"""Issue-time-safe ConvLSTM inference on the un-georeferenced SEVIR replay."""

import hashlib
from functools import lru_cache
from math import pi, sqrt
from pathlib import Path

import h5py
import numpy as np
import torch
from scipy.ndimage import center_of_mass, find_objects, label

from backend.app.schemas.location import EvidenceStatus
from backend.app.schemas.model import ModelArtifact
from backend.app.schemas.replay_grid import LearnedGridCell, LearnedGridForecast, LearnedGridFrame
from backend.app.science.quality_control import RadarQualityControl
from backend.app.science.tracking import CellDetection, PersistentCellTracker
from backend.app.services.grid_replay import ISSUE_INDEX, REPLAY_PATH, grid_replay_metadata
from backend.app.services.model_registry import PROJECT_ROOT, get_model_artifact
from backend.ml.models.convlstm import LightweightConvLSTM


MODEL_ID = "convlstm-sevir-v0"
CONTEXT_FRAMES = 13
FORECAST_FRAMES = 12
TRACKING_DOWNSAMPLE = 4
DETECTION_THRESHOLD_NORMALIZED = 0.5


def verify_checkpoint(artifact: ModelArtifact, checkpoint_path: Path | None = None) -> Path:
    """Refuse missing or modified weights; never substitute random initialization."""
    if checkpoint_path is None:
        path = (PROJECT_ROOT / artifact.checkpoint_path).resolve()
        if not path.is_relative_to(PROJECT_ROOT.resolve()):
            raise ValueError("Registered checkpoint path escapes the repository.")
    else:
        path = Path(checkpoint_path)
    if not path.is_file():
        raise FileNotFoundError(f"Registered checkpoint is missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != artifact.checkpoint_sha256.lower():
        raise ValueError(f"Checkpoint SHA-256 mismatch for {artifact.model_id}.")
    return path


def load_issue_time_context(path: Path = REPLAY_PATH, *, issue_index: int = ISSUE_INDEX) -> torch.Tensor:
    """Read exactly the 13 VIL frames ending at T0, with fixed uint8 scaling."""
    if issue_index < CONTEXT_FRAMES - 1:
        raise ValueError("The issue index does not contain 13 context frames.")
    with h5py.File(path, "r") as handle:
        dataset = handle["vil"]
        if dataset.ndim != 4 or dataset.shape[:3] != (1, 384, 384) or issue_index >= dataset.shape[-1]:
            raise ValueError(f"Unsupported SEVIR VIL shape or issue index: {dataset.shape}.")
        context = np.asarray(
            dataset[0, :, :, issue_index - CONTEXT_FRAMES + 1 : issue_index + 1],
            dtype=np.float32,
        )
    sequence = np.transpose(context, (2, 0, 1))[None, None] / 255.0
    return torch.from_numpy(sequence.copy())


@lru_cache(maxsize=1)
def _registered_model() -> tuple[LightweightConvLSTM, ModelArtifact]:
    artifact = get_model_artifact(MODEL_ID)
    if artifact.architecture != "LightweightConvLSTM" or artifact.status != "UNVALIDATED_PROTOTYPE":
        raise ValueError("Registered model architecture or status does not match the Phase 7 contract.")
    checkpoint = verify_checkpoint(artifact)
    model = LightweightConvLSTM(in_channels=1, hidden_channels=16, seq_out=FORECAST_FRAMES)
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    return model, artifact


@lru_cache(maxsize=1)
def get_learned_grid_forecast() -> LearnedGridForecast:
    metadata = grid_replay_metadata()
    context = load_issue_time_context(issue_index=metadata.issue_index)
    model, artifact = _registered_model()
    with torch.inference_mode():
        predictions = model(context).cpu().numpy()
    expected_shape = (1, 1, FORECAST_FRAMES, 384, 384)
    if predictions.shape != expected_shape or not np.isfinite(predictions).all():
        raise ValueError(f"ConvLSTM returned an invalid forecast tensor: {predictions.shape}.")

    tracker = PersistentCellTracker(max_distance_pixels=18.0)
    qc = RadarQualityControl(
        texture_threshold_db=72.0, minimum_echo_dbz=30.0, maximum_echo_dbz=255.0
    )
    context_values = context.numpy()[0, 0]
    for frame in context_values:
        _track_frame(frame[::TRACKING_DOWNSAMPLE, ::TRACKING_DOWNSAMPLE], tracker, qc)

    frames: list[LearnedGridFrame] = []
    for step, frame in enumerate(predictions[0, 0], start=1):
        reduced = frame[::TRACKING_DOWNSAMPLE, ::TRACKING_DOWNSAMPLE]
        tracks = _track_frame(reduced, tracker, qc)
        cells = [
            LearnedGridCell(
                cell_id=track.track_id,
                centroid_x=round(track.detection.centroid_x, 2),
                centroid_y=round(-track.detection.centroid_y, 2),
                area_pixels=round(track.detection.area_km2),
                radius_pixels=round(sqrt(track.detection.area_km2 / pi), 2),
                peak_normalized=round(track.detection.peak_dbz / 255.0, 4),
            )
            for track in tracks
        ]
        frames.append(
            LearnedGridFrame(
                lead_minutes=step * metadata.time_step_minutes,
                frame_index=metadata.issue_index + step,
                width=reduced.shape[1],
                height=reduced.shape[0],
                values=np.rint(np.clip(reduced, 0, 1) * 255).astype(np.uint8).tolist(),
                cells=cells,
            )
        )

    return LearnedGridForecast(
        event_id=metadata.event_id,
        sample_id=metadata.sample_id,
        issue_frame_index=metadata.issue_index,
        georeferenced=False,
        evidence_status=EvidenceStatus.LEARNED_FORECAST,
        model_version=artifact.model_id,
        model_status="UNVALIDATED_PROTOTYPE",
        checkpoint_sha256=artifact.checkpoint_sha256,
        method="LIGHTWEIGHT_CONVLSTM_SEVIR_VIL",
        source_ids=[metadata.event_id],
        units="NORMALIZED_SEVIR_VIL",
        detection_threshold_normalized=DETECTION_THRESHOLD_NORMALIZED,
        input_shape=list(context.shape),
        output_shape=list(predictions.shape),
        frames=frames,
        limitations=[
            "The model is an unvalidated prototype and has no held-out India evaluation.",
            "Input is observed U.S. SEVIR VIL, not Bhubaneswar radar reflectivity.",
            "The compact event has no georeferencing or absolute issue timestamp.",
            "Pixel-space cells cannot be intersected with WGS84 locations or used for a Jaydev Vihar ETA.",
            "The 0.5 segmentation threshold is numerical and is not a physical hazard threshold.",
            "Fixed uint8 normalization differs from the supplied checkpoint's historical full-event scaling.",
        ],
    )


def _track_frame(
    normalized_field: np.ndarray,
    tracker: PersistentCellTracker,
    qc: RadarQualityControl,
):
    # QC operates as a numerical texture screen here, not calibrated dBZ QC.
    scaled = np.clip(normalized_field, 0, 1).astype(np.float32) * 255.0
    screened = qc.apply(scaled).field
    labels, count = label(screened >= DETECTION_THRESHOLD_NORMALIZED * 255.0)
    slices = find_objects(labels)
    detections: list[CellDetection] = []
    for component_id in range(1, count + 1):
        if slices[component_id - 1] is None:
            continue
        mask = labels == component_id
        area = int(mask.sum())
        if area < 4:
            continue
        row, column = center_of_mass(screened, labels, component_id)
        rows, columns = np.nonzero(mask)
        detections.append(
            CellDetection(
                centroid_x=float(column),
                centroid_y=float(-row),
                area_km2=float(area),  # Tracker cost uses area ratios; units are pixels here.
                peak_dbz=float(scaled[mask].max()),  # Stored as uint8 proxy, never labelled dBZ in output.
                bbox=(float(columns.min()), float(-rows.max()), float(columns.max()), float(-rows.min())),
            )
        )
    return tracker.update(detections, elapsed_minutes=5.0)
