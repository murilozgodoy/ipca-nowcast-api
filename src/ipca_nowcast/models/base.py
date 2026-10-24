"""Common types for forecasters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from ipca_nowcast.features.dataset import DatasetBundle


@dataclass(frozen=True)
class Prediction:
    model: str
    value: float
    pi_lower: float | None = None
    pi_upper: float | None = None


class Forecaster(Protocol):
    """A forecaster takes a dataset bundle and returns a point prediction."""

    name: str

    def predict(self, bundle: DatasetBundle) -> Prediction: ...


def _target_history(bundle: DatasetBundle) -> pd.Series:
    """Last known values of the target series (dropna)."""
    return bundle.target.dropna()
