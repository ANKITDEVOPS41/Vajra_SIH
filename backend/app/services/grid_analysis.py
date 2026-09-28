from functools import lru_cache

import numpy as np
from scipy.ndimage import center_of_mass, find_objects, label

from backend.app.schemas.forecast import GridAnalysis, UngeoreferencedGridCell
from backend.app.schemas.location import EvidenceStatus
from backend.app.science.quality_control import RadarQualityControl
from backend.app.science.tracking import CellDetection, PersistentCellTracker
from backend.app.services.grid_replay import grid_replay_metadata, load_grid_replay_values


@lru_cache(maxsize=16)
def analyze_grid_replay(frame_index: int) -> GridAnalysis:
    """Track the SEVIR sequence in pixel space only.

    The bundled field is VIL in source uint8 values, not calibrated dBZ and not
    georeferenced. The texture screen is therefore a numerical artifact screen,
    never a physical radar-QC claim or a location-intelligence input.
    """
    metadata = grid_replay_metadata()
    if frame_index < 0 or frame_index >= metadata.frame_count:
        raise IndexError(f"Frame index must be between 0 and {metadata.frame_count - 1}.")

    first_index = max(0, frame_index - 3)
    tracker = PersistentCellTracker(max_distance_pixels=45.0)
    qc = RadarQualityControl(
        texture_threshold_db=72.0,
        minimum_echo_dbz=30.0,
        maximum_echo_dbz=255.0,
    )
    latest_detections: list[CellDetection] = []
    for index in range(first_index, frame_index + 1):
        raw_field = load_grid_replay_values(index).astype(np.float32)
        screened = qc.apply(raw_field).field
        latest_detections = _detect_uint8_components(screened)
        tracker.update(latest_detections, elapsed_minutes=metadata.time_step_minutes)

    return GridAnalysis(
        event_id=metadata.event_id,
        frame_index=frame_index,
        evidence_status=EvidenceStatus.DATASET_VERIFIED,
        georeferenced=False,
        field_units="SEVIR_UINT8",
        quality_control_status="TEXTURE_SCREEN_NON_PHYSICAL",
        cells=[
            UngeoreferencedGridCell(
                cell_id=track.track_id,
                centroid_x=round(track.detection.centroid_x, 2),
                centroid_y=round(track.detection.centroid_y, 2),
                area_pixels=round(track.detection.area_km2),
                peak_value=round(track.detection.peak_dbz),
            )
            for track in tracker.active_tracks
        ],
        limitations=[
            "Coordinates are image pixels, not EPSG:4326 longitude/latitude.",
            "SEVIR_UINT8 VIL values are not calibrated dBZ in this compact bundle.",
            "The texture screen is numerical preprocessing only and cannot be interpreted as physical radar QC.",
            "These cells are excluded from Bhubaneswar mapping, forecast polygons, ETA, and location impacts.",
        ],
    )


def _detect_uint8_components(field: np.ndarray) -> list[CellDetection]:
    active = field[field > 0]
    if active.size == 0:
        return []
    threshold = max(40.0, float(np.quantile(active, 0.92)))
    component_labels, count = label(field >= threshold, structure=np.ones((3, 3)))
    slices = find_objects(component_labels)
    detections: list[CellDetection] = []
    for component_id in range(1, count + 1):
        component_slice = slices[component_id - 1]
        if component_slice is None:
            continue
        component = component_labels == component_id
        area = int(component.sum())
        if area < 4:
            continue
        row, column = center_of_mass(field, component_labels, component_id)
        rows, columns = np.nonzero(component)
        detections.append(
            CellDetection(
                centroid_x=float(column),
                centroid_y=float(-row),
                area_km2=float(area),
                peak_dbz=float(field[component].max()),
                bbox=(
                    float(columns.min()),
                    float(-rows.max()),
                    float(columns.max()),
                    float(-rows.min()),
                ),
            )
        )
    return detections
