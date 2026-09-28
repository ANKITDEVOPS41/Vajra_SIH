from dataclasses import dataclass, replace
from math import atan2, degrees, hypot

import numpy as np
from scipy.optimize import linear_sum_assignment


BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class CellDetection:
    centroid_x: float
    centroid_y: float
    area_km2: float
    peak_dbz: float
    bbox: BBox


@dataclass(frozen=True)
class CellTrack:
    track_id: str
    detection: CellDetection
    age_scans: int
    lost_scans: int
    speed_kmh: float
    heading_deg: float | None
    trajectory: tuple[tuple[float, float], ...]


class PersistentCellTracker:
    """Associate cell detections across scans with persistent, deterministic IDs.

    Coordinates are expected in a Cartesian grid where +x is east and +y is north.
    The caller is responsible for reprojecting image row/column coordinates first.
    """

    def __init__(
        self,
        *,
        max_distance_pixels: float = 30.0,
        max_lost_scans: int = 2,
        maximum_assignment_cost: float = 0.85,
    ) -> None:
        if max_distance_pixels <= 0:
            raise ValueError("max_distance_pixels must be positive")
        self.max_distance_pixels = max_distance_pixels
        self.max_lost_scans = max_lost_scans
        self.maximum_assignment_cost = maximum_assignment_cost
        self._next_track_number = 1
        self._tracks: dict[str, CellTrack] = {}

    @property
    def active_tracks(self) -> tuple[CellTrack, ...]:
        return tuple(self._tracks.values())

    def update(
        self,
        detections: list[CellDetection],
        *,
        elapsed_minutes: float,
        grid_resolution_km: float = 1.0,
    ) -> list[CellTrack]:
        if elapsed_minutes <= 0 or grid_resolution_km <= 0:
            raise ValueError("elapsed_minutes and grid_resolution_km must be positive")

        if not self._tracks:
            tracks = [self._new_track(detection) for detection in detections]
            return tracks

        if not detections:
            self._age_unmatched(set())
            return []

        track_ids = list(self._tracks)
        cost = np.full((len(track_ids), len(detections)), np.inf, dtype=np.float64)
        for row, track_id in enumerate(track_ids):
            previous = self._tracks[track_id].detection
            for column, current in enumerate(detections):
                distance = hypot(
                    current.centroid_x - previous.centroid_x,
                    current.centroid_y - previous.centroid_y,
                )
                if distance <= self.max_distance_pixels:
                    area_delta = abs(previous.area_km2 - current.area_km2) / max(
                        previous.area_km2 + current.area_km2, 1e-6
                    )
                    intensity_delta = abs(previous.peak_dbz - current.peak_dbz) / 75.0
                    cost[row, column] = (
                        0.40 * distance / self.max_distance_pixels
                        + 0.35 * (1.0 - _intersection_over_union(previous.bbox, current.bbox))
                        + 0.15 * area_delta
                        + 0.10 * intensity_delta
                    )

        matched_track_rows: set[int] = set()
        matched_detection_columns: set[int] = set()
        if np.isfinite(cost).any():
            finite_cost = np.where(np.isfinite(cost), cost, 1e6)
            rows, columns = linear_sum_assignment(finite_cost)
            for row, column in zip(rows.tolist(), columns.tolist(), strict=True):
                if cost[row, column] > self.maximum_assignment_cost:
                    continue
                track_id = track_ids[row]
                updated = self._update_track(
                    self._tracks[track_id],
                    detections[column],
                    elapsed_minutes,
                    grid_resolution_km,
                )
                self._tracks[track_id] = updated
                matched_track_rows.add(row)
                matched_detection_columns.add(column)

        self._age_unmatched({track_ids[row] for row in matched_track_rows})
        for column, detection in enumerate(detections):
            if column not in matched_detection_columns:
                self._new_track(detection)

        current_ids = {
            track_ids[row] for row in matched_track_rows
        } | {
            track_id
            for track_id, track in self._tracks.items()
            if track.age_scans == 1 and track.lost_scans == 0
        }
        return [self._tracks[track_id] for track_id in self._tracks if track_id in current_ids]

    def _new_track(self, detection: CellDetection) -> CellTrack:
        track_id = f"CELL-A{self._next_track_number:03d}"
        self._next_track_number += 1
        track = CellTrack(
            track_id=track_id,
            detection=detection,
            age_scans=1,
            lost_scans=0,
            speed_kmh=0.0,
            heading_deg=None,
            trajectory=((detection.centroid_x, detection.centroid_y),),
        )
        self._tracks[track_id] = track
        return track

    @staticmethod
    def _update_track(
        previous: CellTrack,
        detection: CellDetection,
        elapsed_minutes: float,
        grid_resolution_km: float,
    ) -> CellTrack:
        dx = detection.centroid_x - previous.detection.centroid_x
        dy = detection.centroid_y - previous.detection.centroid_y
        distance_km = hypot(dx, dy) * grid_resolution_km
        heading = (degrees(atan2(dx, dy)) + 360.0) % 360.0 if distance_km else previous.heading_deg
        trajectory = (*previous.trajectory, (detection.centroid_x, detection.centroid_y))[-12:]
        return CellTrack(
            track_id=previous.track_id,
            detection=detection,
            age_scans=previous.age_scans + 1,
            lost_scans=0,
            speed_kmh=distance_km * 60.0 / elapsed_minutes,
            heading_deg=heading,
            trajectory=trajectory,
        )

    def _age_unmatched(self, matched_ids: set[str]) -> None:
        for track_id in list(self._tracks):
            if track_id in matched_ids:
                continue
            aged = replace(self._tracks[track_id], lost_scans=self._tracks[track_id].lost_scans + 1)
            if aged.lost_scans > self.max_lost_scans:
                del self._tracks[track_id]
            else:
                self._tracks[track_id] = aged


def _intersection_over_union(first: BBox, second: BBox) -> float:
    left = max(first[0], second[0])
    bottom = max(first[1], second[1])
    right = min(first[2], second[2])
    top = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, top - bottom)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0
