import torch
from torch import nn


class WeightedCompositeLoss(nn.Module):
    """MAE plus MSE with additional weight on high-intensity target pixels."""

    def __init__(self, high_intensity_weight: float = 20.0, threshold: float = 0.1) -> None:
        super().__init__()
        self.high_intensity_weight = high_intensity_weight
        self.threshold = threshold

    def forward(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        absolute_error = torch.abs(prediction - target)
        squared_error = torch.square(prediction - target)
        weights = torch.where(
            target > self.threshold,
            torch.full_like(target, self.high_intensity_weight),
            torch.ones_like(target),
        )
        return ((absolute_error + squared_error) * weights).mean()
