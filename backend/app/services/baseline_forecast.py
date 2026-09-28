from dataclasses import dataclass
from datetime import UTC, timedelta
from functools import lru_cache
from math import cos, pi, radians, sin, sqrt

import numpy as np
from scipy.ndimage import center_of_mass, find_objects, label

from backend.app.core.config import settings
from backend.app.schemas.forecast import (
    BaselineForecast,
    CellTrackSnapshot,
    DetectedCellGeometry,
    ForecastCell,
)
from backend.app.schemas.location import EvidenceStatus, GeoPoint
from backend.app.schemas.replay import ReplayFrame, ReplaySession
from backend.app.science.quality_control import RadarQualityControl
from backend.app.science.tracking import CellDetection, CellTrack, PersistentCellTracker
from backend.app.services.replay import get_replay_session


KM_PER_DEGREE_LATITUDE = 111.195
GRID_SIZE = 128
GRID_RESOLUTION_KM = 1.0
DETECTION_THRESHOLD_DBZ = 30.0
FORECAST_LEADS_MINUTES = tuple(range(5, 65, 5))
MINIMUM_EQUIVALENT_RADIUS_KM = 2.5


@dataclass(frozen=True)
class _SpatialGrid:
    center_lat: float
    center_lon: float
    resolution_km: float = GRID_RESOLUTION_KM
    size: int = GRID_SIZE

    @property
    def half_size(self) -> float:
        return (self.size - 1) / 2.0

    def geographic_to_local(self, point: GeoPoint) -> tuple[float, float]:
        east_km = (point.lon - self.center_lon) * KM_PER_DEGREE_LATITUDE * cos(radians(self.center_lat))
        north_km = (point.lat - self.center_lat) * KM_PER_DEGREE_LATITUDE
        return east_km, north_km

    def local_to_geographic(self, east_km: float, north_km: float) -> GeoPoint:
        return GeoPoint(
            lat=self.center_lat + north_km / KM_PER_DEGREE_LATITUDE,
            lon=self.center_lon + east_km / (KM_PER_DEGREE_LATITUDE * cos(radians(self.center_lat))),
        )

    def local_to_pixel(self, east_km: float, north_km: float) -> tuple[float, float]:
        return (
            self.half_size + east_km / self.resolution_km,
            self.half_size - north_km / self.resolution_km,
        )

    def pixel_to_local(self, column: float, row: float) -> tuple[float, float]:
        return (
            (column - self.half_size) * self.resolution_km,
            (self.half_size - row) * self.resolution_km,
        )


@lru_cache(maxsize=1)
def get_baseline_forecast() -> BaselineForecast:
    """Build a deterministic baseline from issue-time-safe synthetic replay frames.

    The spatial coordinate system comes from the Bhubaneswar simulation fixture,
    not from SEVIR. This keeps the demonstration useful without assigning India
    coordinates to the bundled un-georeferenced U.S. benchmark field.
    """
    session = get_replay_session(settings.active_replay_event)
    if session is None:
        raise FileNotFoundError(f"Active replay event '{settings.active_replay_event}' was not found.")
    if session.evidence_status != EvidenceStatus.SIMULATED:
        raise ValueError("The location baseline requires an explicitly simulated georeferenced replay event.")

    grid = _SpatialGrid(center_lat=20.30, center_lon=85.82)
    observed_frames = sorted(
        (
            frame
            for frame in session.frames
            if frame.available_at_issue_time and frame.valid_time <= session.issue_time
        ),
        key=lambda frame: frame.valid_time,
    )
    if len(observed_frames) < 2:
        raise ValueError("At least two issue-time-safe frames are required for a velocity baseline.")

    tracker = PersistentCellTracker(max_distance_pixels=40.0)
    qc = RadarQualityControl(texture_threshold_db=24.0)
    latest_detections: list[CellDetection] = []
    latest_qc_removed_pixels = 0
    previous_time = None
    for frame in observed_frames:
        radar_grid = _render_synthetic_reflectivity(frame, grid)
        qc_result = qc.apply(radar_grid)
        detections = _detect_cells(qc_result.field, grid)
        if previous_time is None:
            elapsed_minutes = session.timeline_step_minutes
        else:
            elapsed_minutes = int((frame.valid_time - previous_time).total_seconds() / 60.0)
        tracker.update(detections, elapsed_minutes=elapsed_minutes, grid_resolution_km=grid.resolution_km)
        previous_time = frame.valid_time
        latest_detections = detections
        latest_qc_removed_pixels = qc_result.removed_pixel_count

    detection_by_position = {
        _position_key(detection.centroid_x, detection.centroid_y): detection
        for detection in latest_detections
    }
    current_cells = [
        _detected_geometry(track, grid, latest_qc_removed_pixels)
        for track in tracker.active_tracks
        if _position_key(track.detection.centroid_x, track.detection.centroid_y) in detection_by_position
    ]
    forecasts = _advect_tracks(
        tracker.active_tracks,
        grid,
        issue_time=session.issue_time,
        step_minutes=session.timeline_step_minutes,
    )
    return BaselineForecast(
        event_id=session.event_id,
        issue_time=session.issue_time,
        evidence_status=EvidenceStatus.SIMULATED,
        mode="REPLAY",
        method="CONSTANT_VELOCITY_EQUIVALENT_AREA",
        detection_threshold_dbz=DETECTION_THRESHOLD_DBZ,
        tracks=[_track_snapshot(track, grid) for track in tracker.active_tracks],
        current_cells=current_cells,
        forecast_cells=forecasts,
        source_ids=["sim-radar-grid"],
        limitations=[
            "Cell fields are generated from the declared Bhubaneswar simulation fixture for pipeline testing.",
            "The baseline assumes constant velocity and constant equivalent-area footprint through T+60.",
            "No growth, decay, terrain, wind, uncertainty calibration, or meteorological verification is included.",
            "SEVIR VIL is processed separately as an un-georeferenced dataset field and is not used for India intersections.",
            "Location impacts are simulated engineering outputs, not operational weather guidance.",
        ],
    )


def _render_synthetic_reflectivity(frame: ReplayFrame, grid: _SpatialGrid) -> np.ndarray:
    """Rasterize the fixture's declared cell objects onto a local 1 km grid."""
    rows, columns = np.mgrid[0 : grid.size, 0 : grid.size]
    field = np.zeros((grid.size, grid.size), dtype=np.float32)
    for cell in frame.cells:
        east_km, north_km = grid.geographic_to_local(cell.centroid)
        center_column, center_row = grid.local_to_pixel(east_km, north_km)
        sigma_pixels = 3.2
        gaussian = cell.max_reflectivity_dbz * np.exp(
            -((columns - center_column) ** 2 + (rows - center_row) ** 2) / (2.0 * sigma_pixels**2)
        )
        field = np.maximum(field, gaussian.astype(np.float32))
    return field


def _detect_cells(field: np.ndarray, grid: _SpatialGrid) -> list[CellDetection]:
    component_labels, component_count = label(field >= DETECTION_THRESHOLD_DBZ, structure=np.ones((3, 3)))
    components = find_objects(component_labels)
    detections: list[CellDetection] = []
    for component_id in range(1, component_count + 1):
        component_slice = components[component_id - 1]
        if component_slice is None:
            continue
        component_mask = component_labels == component_id
        pixel_count = int(component_mask.sum())
        if pixel_count < 4:
            continue
        weighted_row, weighted_column = center_of_mass(field, component_labels, component_id)
        east_km, north_km = grid.pixel_to_local(float(weighted_column), float(weighted_row))
        rows, columns = np.nonzero(component_mask)
        east_values, north_values = grid.pixel_to_local(columns.astype(float), rows.astype(float))
        detections.append(
            CellDetection(
                centroid_x=east_km,
                centroid_y=north_km,
                area_km2=pixel_count * grid.resolution_km**2,
                peak_dbz=float(field[component_mask].max()),
                bbox=(
                    float(np.min(east_values)),
                    float(np.min(north_values)),
                    float(np.max(east_values)),
                    float(np.max(north_values)),
                ),
            )
        )
    return detections


def _detected_geometry(track: CellTrack, grid: _SpatialGrid, qc_removed_pixels: int) -> DetectedCellGeometry:
    radius_km = max(sqrt(track.detection.area_km2 / pi), MINIMUM_EQUIVALENT_RADIUS_KM)
    return DetectedCellGeometry(
        cell_id=track.track_id,
        centroid=grid.local_to_geographic(track.detection.centroid_x, track.detection.centroid_y),
        polygon=_equivalent_area_polygon(track.detection.centroid_x, track.detection.centroid_y, radius_km, grid),
        area_km2=track.detection.area_km2,
        equivalent_radius_km=radius_km,
        max_reflectivity_dbz=track.detection.peak_dbz,
        qc_removed_pixels=qc_removed_pixels,
    )


def _track_snapshot(track: CellTrack, grid: _SpatialGrid) -> CellTrackSnapshot:
    return CellTrackSnapshot(
        cell_id=track.track_id,
        age_scans=track.age_scans,
        centroid=grid.local_to_geographic(track.detection.centroid_x, track.detection.centroid_y),
        speed_kmh=round(track.speed_kmh, 2),
        heading_deg=round(track.heading_deg, 2) if track.heading_deg is not None else None,
        trajectory=[grid.local_to_geographic(east, north) for east, north in track.trajectory],
    )


def _advect_tracks(
    tracks: tuple[CellTrack, ...],
    grid: _SpatialGrid,
    *,
    issue_time,
    step_minutes: int,
) -> list[ForecastCell]:
    forecasts: list[ForecastCell] = []
    for track in tracks:
        if len(track.trajectory) < 2:
            continue
        previous_east, previous_north = track.trajectory[-2]
        current_east, current_north = track.trajectory[-1]
        east_per_minute = (current_east - previous_east) / step_minutes
        north_per_minute = (current_north - previous_north) / step_minutes
        radius_km = max(sqrt(track.detection.area_km2 / pi), MINIMUM_EQUIVALENT_RADIUS_KM)
        for lead_minutes in FORECAST_LEADS_MINUTES:
            east_km = current_east + east_per_minute * lead_minutes
            north_km = current_north + north_per_minute * lead_minutes
            forecasts.append(
                ForecastCell(
                    forecast_id=f"baseline-{track.track_id.lower()}-t{lead_minutes:03d}",
                    cell_id=track.track_id,
                    lead_minutes=lead_minutes,
                    valid_time=issue_time + timedelta(minutes=lead_minutes),
                    centroid=grid.local_to_geographic(east_km, north_km),
                    polygon=_equivalent_area_polygon(east_km, north_km, radius_km, grid),
                    equivalent_radius_km=radius_km,
                    max_reflectivity_dbz=track.detection.peak_dbz,
                    method="CONSTANT_VELOCITY_EQUIVALENT_AREA",
                    evidence_status=EvidenceStatus.SIMULATED,
                    source_ids=["sim-radar-grid"],
                )
            )
    return forecasts


def _equivalent_area_polygon(
    east_km: float,
    north_km: float,
    radius_km: float,
    grid: _SpatialGrid,
) -> list[GeoPoint]:
    return [
        grid.local_to_geographic(
            east_km + radius_km * sin(2.0 * pi * index / 24.0),
            north_km + radius_km * cos(2.0 * pi * index / 24.0),
        )
        for index in range(24)
    ]


def _position_key(east_km: float, north_km: float) -> tuple[int, int]:
    return round(east_km * 10), round(north_km * 10)
