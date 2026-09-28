from dataclasses import dataclass
from typing import Iterable, Protocol


class TorchModule(Protocol):
    def train(self) -> None: ...
    def __call__(self, batch: object) -> object: ...


@dataclass(frozen=True)
class TrainingMetrics:
    epoch: int
    loss: float
    batches: int


def train_forecast_impact_model(
    model: TorchModule,
    dataloader: Iterable[object],
    optimizer: object,
    loss_fn: object,
    epochs: int = 5,
) -> list[TrainingMetrics]:
    """Framework-neutral wrapper for the prototype PyTorch training loop.

    The previous prototype loop can be moved behind this function without tying the
    FastAPI runtime to training-only dependencies. Runtime inference should expose a
    separate adapter once model artifacts are finalized.
    """
    metrics: list[TrainingMetrics] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        batches = 0

        for batch in dataloader:
            optimizer.zero_grad()
            prediction = model(batch)
            loss = loss_fn(prediction, batch)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu().item())
            batches += 1

        metrics.append(
            TrainingMetrics(
                epoch=epoch,
                loss=round(total_loss / max(batches, 1), 6),
                batches=batches,
            )
        )

    return metrics
