from dataclasses import dataclass

import numpy as np
from scipy.ndimage import uniform_filter


@dataclass(frozen=True)
class ContingencyTable:
    hits: int
    misses: int
    false_alarms: int
    correct_negatives: int


@dataclass(frozen=True)
class CategoricalScores:
    csi: float | None
    pod: float | None
    far: float | None
    frequency_bias: float | None
    heidke_skill_score: float | None


def contingency_table(
    forecast: np.ndarray,
    observation: np.ndarray,
    *,
    threshold: float,
) -> ContingencyTable:
    forecast_array, observation_array = _aligned_arrays(forecast, observation)
    forecast_event = forecast_array >= threshold
    observed_event = observation_array >= threshold
    return ContingencyTable(
        hits=int(np.count_nonzero(forecast_event & observed_event)),
        misses=int(np.count_nonzero(~forecast_event & observed_event)),
        false_alarms=int(np.count_nonzero(forecast_event & ~observed_event)),
        correct_negatives=int(np.count_nonzero(~forecast_event & ~observed_event)),
    )


def categorical_scores(table: ContingencyTable) -> CategoricalScores:
    event_forecast_total = table.hits + table.false_alarms
    event_observation_total = table.hits + table.misses
    csi_denominator = table.hits + table.misses + table.false_alarms
    total = csi_denominator + table.correct_negatives
    hss_denominator = (
        (table.hits + table.misses) * (table.misses + table.correct_negatives)
        + (table.hits + table.false_alarms)
        * (table.false_alarms + table.correct_negatives)
    )
    return CategoricalScores(
        csi=_divide(table.hits, csi_denominator),
        pod=_divide(table.hits, event_observation_total),
        far=_divide(table.false_alarms, event_forecast_total),
        frequency_bias=_divide(event_forecast_total, event_observation_total),
        heidke_skill_score=_divide(
            2 * (table.hits * table.correct_negatives - table.misses * table.false_alarms),
            hss_denominator,
        ) if total else None,
    )


def equitable_threat_score(table: ContingencyTable) -> float | None:
    """Gilbert skill score, adjusted for hits expected by random chance."""
    counts = (table.hits, table.misses, table.false_alarms, table.correct_negatives)
    if any(count < 0 for count in counts):
        raise ValueError("Contingency counts must be nonnegative")
    total = sum(counts)
    if total == 0:
        return None
    random_hits = (
        (table.hits + table.misses) * (table.hits + table.false_alarms) / total
    )
    denominator = table.hits + table.misses + table.false_alarms - random_hits
    return (table.hits - random_hits) / denominator if denominator else None


def fractions_skill_score(
    forecast: np.ndarray,
    observation: np.ndarray,
    *,
    threshold: float,
    neighborhood_size: int,
) -> float | None:
    if neighborhood_size < 1 or neighborhood_size % 2 == 0:
        raise ValueError("neighborhood_size must be a positive odd integer")
    forecast_array, observation_array = _aligned_arrays(forecast, observation)
    forecast_fraction = uniform_filter(
        (forecast_array >= threshold).astype(np.float32),
        size=neighborhood_size,
        mode="constant",
    )
    observation_fraction = uniform_filter(
        (observation_array >= threshold).astype(np.float32),
        size=neighborhood_size,
        mode="constant",
    )
    denominator = float(np.mean(forecast_fraction**2 + observation_fraction**2))
    if denominator == 0.0:
        return None
    return 1.0 - float(np.mean((forecast_fraction - observation_fraction) ** 2)) / denominator


def brier_score(probability_forecast: np.ndarray, binary_observation: np.ndarray) -> float:
    forecast, observation = _aligned_arrays(probability_forecast, binary_observation)
    if np.any((forecast < 0.0) | (forecast > 1.0)):
        raise ValueError("probability forecasts must be in [0, 1]")
    if np.any((observation != 0.0) & (observation != 1.0)):
        raise ValueError("binary observations must contain only 0 and 1")
    return float(np.mean((forecast - observation) ** 2))


def _aligned_arrays(first: np.ndarray, second: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    first_array = np.asarray(first, dtype=np.float64)
    second_array = np.asarray(second, dtype=np.float64)
    if first_array.shape != second_array.shape:
        raise ValueError("forecast and observation must have the same shape")
    if first_array.size == 0:
        raise ValueError("verification arrays cannot be empty")
    if not np.isfinite(first_array).all() or not np.isfinite(second_array).all():
        raise ValueError("verification arrays must contain finite values")
    return first_array, second_array


def _divide(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
