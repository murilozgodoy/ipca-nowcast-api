"""Simple-mean combination forecaster."""

from __future__ import annotations

from dataclasses import dataclass, field

from ipca_nowcast.features.dataset import DatasetBundle
from ipca_nowcast.models.base import Forecaster, Prediction


@dataclass
class MeanCombination:
    components: list[Forecaster] = field(default_factory=list)
    name: str = "combo_mean"

    def predict(self, bundle: DatasetBundle) -> Prediction:
        preds = [c.predict(bundle).value for c in self.components]
        if not preds:
            return Prediction(self.name, value=0.0)
        return Prediction(self.name, value=sum(preds) / len(preds))
