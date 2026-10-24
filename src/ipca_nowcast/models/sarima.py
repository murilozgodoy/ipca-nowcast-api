"""SARIMA forecaster for monthly IPCA."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from statsmodels.tsa.statespace.sarimax import SARIMAX

from ipca_nowcast.features.dataset import DatasetBundle
from ipca_nowcast.models.base import Prediction, _target_history


@dataclass
class SarimaForecaster:
    order: tuple[int, int, int] = (1, 0, 1)
    seasonal_order: tuple[int, int, int, int] = (1, 1, 1, 12)
    name: str = "sarima"

    def predict(self, bundle: DatasetBundle) -> Prediction:
        y = _target_history(bundle)
        if len(y) < 36:
            return Prediction(self.name, value=float(y.iloc[-1]) if not y.empty else 0.0)
        steps = max(1, bundle.horizon + 1 if bundle.horizon > 0 else 1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                model = SARIMAX(
                    y.values,
                    order=self.order,
                    seasonal_order=self.seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = model.fit(disp=False, maxiter=100)
                forecast = fit.get_forecast(steps=steps)
                mean = float(forecast.predicted_mean[-1])
                ci = forecast.conf_int(alpha=0.2)
                lower = float(ci[-1, 0])
                upper = float(ci[-1, 1])
                return Prediction(self.name, value=mean, pi_lower=lower, pi_upper=upper)
            except Exception:
                return Prediction(self.name, value=float(y.iloc[-1]))
