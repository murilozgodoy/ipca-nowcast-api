"""Trivial baselines and the Focus (median) benchmark."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ipca_nowcast.db.models import FocusExpectation
from ipca_nowcast.features.dataset import DatasetBundle
from ipca_nowcast.models.base import Prediction, _target_history


@dataclass
class RandomWalk:
    """Prediction = last known value of the target."""

    name: str = "random_walk"

    def predict(self, bundle: DatasetBundle) -> Prediction:
        hist = _target_history(bundle)
        if hist.empty:
            return Prediction(self.name, value=0.0)
        return Prediction(self.name, value=float(hist.iloc[-1]))


@dataclass
class HistoricalMean:
    """Prediction = mean of the last `window` months (default: all history)."""

    window: int | None = None
    name: str = "historical_mean"

    def predict(self, bundle: DatasetBundle) -> Prediction:
        hist = _target_history(bundle)
        if hist.empty:
            return Prediction(self.name, value=0.0)
        if self.window:
            hist = hist.tail(self.window)
        return Prediction(self.name, value=float(hist.mean()))


@dataclass
class SeasonalNaive:
    """Prediction = value from the same calendar month, 12 months earlier."""

    name: str = "seasonal_naive"

    def predict(self, bundle: DatasetBundle) -> Prediction:
        hist = _target_history(bundle)
        if hist.empty:
            return Prediction(self.name, value=0.0)
        target_month = bundle.target_month
        same_month_last_year = dt.date(target_month.year - 1, target_month.month, 1)
        ts = pd.Timestamp(same_month_last_year)
        if ts in hist.index:
            return Prediction(self.name, value=float(hist.loc[ts]))
        return Prediction(self.name, value=float(hist.iloc[-1]))


class FocusBaseline:
    """Latest Focus median expectation for the target month as of ``origin_date``.

    The Focus benchmark is the **median known at the origin_date**, never a
    later revision — this is the core anti-look-ahead rule from the prompt.
    """

    name: str = "focus_median"

    def __init__(self, session: Session, base_calculo: int = 0) -> None:
        self.session = session
        self.base_calculo = base_calculo

    def predict(self, bundle: DatasetBundle) -> Prediction:
        stmt = (
            select(FocusExpectation)
            .where(FocusExpectation.indicator == "IPCA")
            .where(FocusExpectation.reference_date == bundle.target_month)
            .where(FocusExpectation.collected_at <= bundle.origin_date)
            .where(FocusExpectation.base_calculo == self.base_calculo)
            .order_by(FocusExpectation.collected_at.desc())
        )
        row = self.session.scalars(stmt).first()
        if row is None or row.median is None:
            # Fall back to RandomWalk if Focus is unavailable at this origin.
            return RandomWalk(name="focus_median").predict(bundle)
        return Prediction(self.name, value=float(row.median))
