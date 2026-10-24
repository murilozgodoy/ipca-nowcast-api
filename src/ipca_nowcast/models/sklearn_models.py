"""ElasticNet and GradientBoosting wrappers on top of the real-time dataset.

Both forecasters produce an 80% prediction interval using the empirical
distribution of **in-sample residuals** — i.e., ``PI = pred ± q_90(|e|)``
where ``e_i = y_i - ŷ_i`` on the training set. This is the standard
"residual bootstrap" shortcut: no bootstrap resampling, just the empirical
quantile of the residuals shifted around the point forecast. SARIMA
already provides analytical PIs; combos just carry theirs through.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import ElasticNetCV

from ipca_nowcast.features.dataset import DatasetBundle
from ipca_nowcast.models.base import Prediction, _target_history


def _build_xy(bundle: DatasetBundle) -> tuple[pd.DataFrame, pd.Series]:
    """Align features and target, dropping rows where either is missing."""
    y = _target_history(bundle)
    if y.empty:
        return pd.DataFrame(), y
    X = bundle.features.loc[bundle.features.index.isin(y.index)].copy()
    y = y.loc[X.index]
    # Fill remaining NaN features with the column median (defensive).
    X = X.fillna(X.median(numeric_only=True))
    X = X.fillna(0.0)
    return X, y


def _latest_feature_row(bundle: DatasetBundle) -> pd.DataFrame | None:
    """Grab the last row of the feature frame (features for the target month)."""
    if bundle.features.empty:
        return None
    row = bundle.features.iloc[[-1]].copy()
    return row.fillna(bundle.features.median(numeric_only=True)).fillna(0.0)


def _residual_pi(pred: float, residuals: np.ndarray, alpha: float = 0.1) -> tuple[float, float]:
    """80% PI = (pred + q_alpha(e), pred + q_{1-alpha}(e)) using empirical quantiles."""
    if residuals.size < 8:
        return (pred, pred)
    low = float(np.quantile(residuals, alpha))
    high = float(np.quantile(residuals, 1 - alpha))
    return (pred + low, pred + high)


@dataclass
class ElasticNetForecaster:
    name: str = "elasticnet"
    random_state: int = 42

    def predict(self, bundle: DatasetBundle) -> Prediction:
        X, y = _build_xy(bundle)
        if len(y) < 24 or X.empty:
            fallback = float(y.iloc[-1]) if not y.empty else 0.0
            return Prediction(self.name, value=fallback)
        model = ElasticNetCV(
            l1_ratio=[0.1, 0.5, 0.9],
            alphas=np.logspace(-3, 1, 20),
            max_iter=5000,
            cv=min(5, len(y) // 4),
            random_state=self.random_state,
        )
        model.fit(X.values, y.values)
        latest = _latest_feature_row(bundle)
        if latest is None:
            fallback = float(y.iloc[-1])
            return Prediction(self.name, value=fallback)
        pred = float(model.predict(latest.values)[0])
        residuals = y.values - model.predict(X.values)
        lower, upper = _residual_pi(pred, residuals)
        return Prediction(self.name, value=pred, pi_lower=lower, pi_upper=upper)


@dataclass
class GradientBoostingForecaster:
    name: str = "gradient_boosting"
    random_state: int = 42

    def predict(self, bundle: DatasetBundle) -> Prediction:
        X, y = _build_xy(bundle)
        if len(y) < 24 or X.empty:
            fallback = float(y.iloc[-1]) if not y.empty else 0.0
            return Prediction(self.name, value=fallback)
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            random_state=self.random_state,
        )
        model.fit(X.values, y.values)
        latest = _latest_feature_row(bundle)
        if latest is None:
            fallback = float(y.iloc[-1])
            return Prediction(self.name, value=fallback)
        pred = float(model.predict(latest.values)[0])
        residuals = y.values - model.predict(X.values)
        lower, upper = _residual_pi(pred, residuals)
        return Prediction(self.name, value=pred, pi_lower=lower, pi_upper=upper)
