"""Context-channel inventory and non-probabilistic hazard screening."""

from pathlib import Path
from typing import Literal

import h5py

from backend.app.schemas.intelligence import (
    HazardIndicator,
    HazardScreening,
    ModalityChannel,
    MultimodalStatus,
)
from backend.app.schemas.location import EvidenceStatus
from backend.app.services.baseline_forecast import get_baseline_forecast
from backend.app.services.grid_replay import EVENT_ID, ISSUE_INDEX, REPLAY_PATH


REFLECTIVITY_SCREEN_DBZ = 45.0
VIL_NUMERICAL_SCREEN = 0.5


def modality_status(path: Path = REPLAY_PATH) -> MultimodalStatus:
    """Inventory actual file channels; shape alone is not time/space registration."""
    with h5py.File(path, "r") as handle:
        if "vil" not in handle or handle["vil"].ndim != 4:
            raise ValueError("The SEVIR replay has no usable VIL sequence.")
        vil = handle["vil"]
        vil_frames = min(13, int(vil.shape[-1]))
        if vil_frames < 13:
            raise ValueError("The SEVIR replay lacks 13 issue-time VIL context frames.")
        ir = handle.get("ir107")
        has_ir = ir is not None

    return MultimodalStatus(
        event_id=EVENT_ID,
        issue_frame_index=ISSUE_INDEX,
        fusion_mode="VIL_ONLY_FALLBACK",
        model_input_channels=["SEVIR_VIL"],
        modalities=[
            ModalityChannel(
                source_id="SEVIR_VIL",
                availability="AVAILABLE",
                role="MODEL_INPUT",
                evidence_status=EvidenceStatus.DATASET_VERIFIED,
                aligned_context_frames=vil_frames,
                reason="Observed VIL frames 0-12 feed the single-channel ConvLSTM; no WGS84 georeferencing.",
            ),
            ModalityChannel(
                source_id="SEVIR_IR107",
                availability="AVAILABLE" if has_ir else "NOT_AVAILABLE",
                role="CONTEXT_ONLY" if has_ir else "UNAVAILABLE",
                evidence_status=EvidenceStatus.DATASET_VERIFIED if has_ir else None,
                aligned_context_frames=0,
                reason=(
                    "IR107 is present, but spatial/time registration and thermal scaling are not verified; excluded from inference."
                    if has_ir else "IR107 is absent from the bundled H5; no aligned thermal layer can be rendered."
                ),
            ),
            ModalityChannel(
                source_id="INSAT_3D_IR",
                availability="NOT_AVAILABLE",
                role="UNAVAILABLE",
                evidence_status=None,
                aligned_context_frames=0,
                reason="No authorized INSAT-3D feed, raster, or co-registration is configured.",
            ),
        ],
    )


def _screen(
    cell_id: str,
    lead_minutes: int,
    value: float,
    *,
    learned: bool,
) -> list[HazardIndicator]:
    threshold = VIL_NUMERICAL_SCREEN if learned else REFLECTIVITY_SCREEN_DBZ
    evidence = EvidenceStatus.LEARNED_FORECAST if learned else EvidenceStatus.SIMULATED
    core = HazardIndicator(
        cell_id=cell_id,
        lead_minutes=lead_minutes,
        indicator="NORMALIZED_VIL_CORE" if learned else "HIGH_REFLECTIVITY_CORE",
        state="THRESHOLD_MET" if value >= threshold else "BELOW_THRESHOLD",
        value=round(value, 4) if learned else round(value, 1),
        threshold=threshold,
        unit="normalized 0-1" if learned else "dBZ",
        method="MODEL_PIXEL_PEAK_GE_0_5" if learned else "CELL_PEAK_DBZ_GE_45",
        evidence_status=evidence,
        derivation_status=EvidenceStatus.INFERRED,
        uncertainty_status="NOT_CALIBRATED",
        reason=(
            "Numerical segmentation screen on uncalibrated, un-georeferenced ConvLSTM output; not physical VIL or a hazard warning."
            if learned else "Engineering reflectivity screen on synthetic cell intensity; not observed weather or verified severity."
        ),
    )
    withheld = [
        HazardIndicator(
            cell_id=cell_id,
            lead_minutes=lead_minutes,
            indicator=indicator,
            state="NOT_EVALUABLE",
            value=None,
            threshold=None,
            unit=None,
            method="WITHHELD_MISSING_VALIDATION_DATA",
            evidence_status=evidence,
            derivation_status=EvidenceStatus.INFERRED,
            uncertainty_status="NOT_CALIBRATED",
            reason=reason,
        )
        for indicator, reason in (
            ("CLOUDBURST_RISK", "Requires high-frequency gauge/AWS or calibrated radar QPE and a validated event definition."),
            ("HAIL_RISK", "Requires calibrated multi-parameter radar/environmental evidence and verified hail labels."),
        )
    ]
    return [core, *withheld]


def assess_hazards(forecast_mode: Literal["BASELINE", "LEARNED"]) -> HazardScreening:
    if forecast_mode == "LEARNED":
        from backend.app.services.learned_forecast import get_learned_grid_forecast

        forecast = get_learned_grid_forecast()
        indicators = [
            indicator
            for frame in forecast.frames
            for cell in frame.cells
            for indicator in _screen(cell.cell_id, frame.lead_minutes, cell.peak_normalized, learned=True)
        ]
        return HazardScreening(
            event_id=forecast.event_id,
            forecast_mode="LEARNED",
            modality_mode="VIL_ONLY_FALLBACK",
            georeferenced=False,
            model_version=forecast.model_version,
            model_status=forecast.model_status,
            indicators=indicators,
            limitations=[
                "Only normalized numerical VIL response is screened; no calibrated physical intensity or India coordinates.",
                "Cloudburst and hail risk and numerical uncertainty are withheld pending validation.",
            ],
        )

    forecast = get_baseline_forecast()
    cells = [(cell.cell_id, 0, cell.max_reflectivity_dbz) for cell in forecast.current_cells]
    cells.extend((cell.cell_id, cell.lead_minutes, cell.max_reflectivity_dbz) for cell in forecast.forecast_cells)
    return HazardScreening(
        event_id=forecast.event_id,
        forecast_mode="BASELINE",
        modality_mode="SIMULATED_RADAR_ONLY",
        georeferenced=True,
        model_version=None,
        model_status=None,
        indicators=[indicator for cell_id, lead, value in cells for indicator in _screen(cell_id, lead, value, learned=False)],
        limitations=[
            "Reflectivity is from a deterministic simulated radar fixture and is held constant in the baseline forecast.",
            "The 45 dBZ screen is an engineering threshold, not a validated local warning or risk probability.",
            "Cloudburst and hail risk and numerical uncertainty are withheld pending validation.",
        ],
    )
