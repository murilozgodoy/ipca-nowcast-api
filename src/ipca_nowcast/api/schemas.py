"""Pydantic v2 schemas for the public API."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["up", "down"]


class SeriesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    source: str
    unit: str
    frequency: str
    publication_lag_days: int
    is_target: bool


class Observation(BaseModel):
    reference_date: dt.date
    value: float | None


class SeriesDetail(SeriesOut):
    first_date: dt.date | None
    last_date: dt.date | None
    n: int
    observations: list[Observation]


class ForecastPoint(BaseModel):
    model: str
    origin_date: dt.date
    reference_date: dt.date
    horizon: int
    prediction: float
    pi_lower: float | None = None
    pi_upper: float | None = None


class NowcastRow(BaseModel):
    model: str
    prediction: float
    pi_lower: float | None = None
    pi_upper: float | None = None


class NowcastLatest(BaseModel):
    origin_date: dt.date
    target_month: dt.date
    horizon: int
    models: list[NowcastRow]
    focus_median: float | None


class BacktestMetric(BaseModel):
    model: str
    horizon: int
    subperiod: str
    n: int
    rmse: float | None
    mae: float | None
    bias: float | None
    rmse_vs_focus: float | None
    dm_stat_vs_focus: float | None
    dm_pvalue_vs_focus: float | None


class FocusLatestPoint(BaseModel):
    reference_date: dt.date
    collected_at: dt.date
    median: float | None
    mean: float | None
    std_dev: float | None
    n_respondents: int | None


class Paginated(BaseModel):
    """Minimal pagination envelope."""

    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    total: int = 0
