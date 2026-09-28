from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset


NormalizationMode = Literal["sevir_uint8", "legacy_event_minmax"]


class SEVIRDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """Loads VIL sequences without using future frames to set the default scale."""

    def __init__(
        self,
        vil_path: str | Path,
        context_frames: int = 13,
        forecast_frames: int = 12,
        normalization: NormalizationMode = "sevir_uint8",
    ) -> None:
        self.vil_path = Path(vil_path)
        self.context_frames = context_frames
        self.forecast_frames = forecast_frames
        self.normalization = normalization
        if not self.vil_path.is_file():
            raise FileNotFoundError(f"SEVIR VIL file not found: {self.vil_path}")

        with h5py.File(self.vil_path, "r") as handle:
            self.event_ids = [value.decode("ascii") for value in handle["id"][:]] if "id" in handle else []
            self.vil = handle["vil"][:]

        if self.vil.ndim != 4:
            raise ValueError(f"Expected a 4D VIL array, received shape {self.vil.shape}.")
        if self.vil.shape[-1] < context_frames + forecast_frames:
            raise ValueError("SEVIR event does not contain enough temporal frames.")
        self.vil = np.transpose(self.vil, (0, 3, 1, 2))

    def __len__(self) -> int:
        return int(self.vil.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        event = self.vil[index].astype(np.float32)
        if self.normalization == "sevir_uint8":
            event = event / 255.0
        else:
            # Reproduces the supplied checkpoint preprocessing only. It is not claim-safe
            # because the full event, including future frames, defines the scale.
            minimum = float(event.min())
            maximum = float(event.max())
            event = event if maximum == minimum else (event - minimum) / (maximum - minimum)

        context = event[: self.context_frames, None, :, :]
        target = event[self.context_frames : self.context_frames + self.forecast_frames, None, :, :]
        return torch.from_numpy(context), torch.from_numpy(target)
