"""Real-time dataset builder.

The hard invariant is that **no feature value whose publication date is
after `origin_date` may enter the dataset**. We enforce this by trimming
each series to observations whose reference date plus its configured
``publication_lag_days`` falls on or before ``origin_date``.

The target is the IPCA monthly variation (``sgs.433``) at
``month(origin_date) + horizon``. When ``horizon == 0`` this is a nowcast
(the target month is the one that would be published around
``origin_date + publication_lag_days`` days).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from ipca_nowcast.db.models import Observation, Series

DEFAULT_LAGS: tuple[int, ...] = (1, 3, 6, 12)
TARGET_CODE = "sgs.433"


@dataclass(frozen=True)
class DatasetBundle:
    """Features frame + target series + metadata.

    Attributes:
        features: monthly DataFrame indexed by month-start date (``ds``).
        target: series indexed by month-start date (``ds``).
        origin_date: the as-of date used to clip features (no leakage).
        horizon: number of calendar months between origin and target month.
        target_month: month covered by the target observation.
        asof_cutoffs: per-series latest included ``reference_date``.
    """

    features: pd.DataFrame
    target: pd.Series
    origin_date: dt.date
    horizon: int
    target_month: dt.date
    asof_cutoffs: dict[str, dt.date | None]


def _month_start(d: dt.date) -> dt.date:
    return dt.date(d.year, d.month, 1)


def _to_monthly(points: list[tuple[dt.date, Decimal | None]], frequency: str) -> pd.Series:
    """Convert raw observations into a month-indexed numeric Series.

    Daily and monthly series are collapsed to the first day of the month.
    Daily series use the last available observation of each month (end-of-
    month value), which is the usual real-time convention for financial
    variables (FX, policy rate). Monthly series keep their value.
    """
    if not points:
        return pd.Series(dtype="float64", name="value")
    rows = [(_month_start(d), float(v) if v is not None else float("nan")) for d, v in points]
    series = pd.Series(dict(rows))
    series.index = pd.to_datetime(series.index)
    series = series.sort_index()
    if frequency == "daily":
        # Use last daily reading within the month (resample 'MS' with last()).
        series.index = pd.to_datetime(series.index)
        full_dates = pd.to_datetime([d for d, _ in points])
        full_values = pd.Series(
            [float(v) if v is not None else float("nan") for _, v in points], index=full_dates
        ).sort_index()
        series = full_values.resample("MS").last()
    series.name = "value"
    return series


def _publication_date(ref: dt.date, lag_days: int, frequency: str) -> dt.date:
    """Approximate the date on which an observation becomes public.

    For monthly series the lag is measured from the **end of the reference
    month** (e.g. the IPCA for October is released ~11 days after Oct 31,
    i.e. around Nov 11). For daily/weekly series the lag is counted from
    the reference date itself.
    """
    if frequency == "monthly":
        end_of_month = (ref + relativedelta(months=1)) - dt.timedelta(days=1)
        return end_of_month + dt.timedelta(days=lag_days)
    return ref + dt.timedelta(days=lag_days)


def _clip_to_origin(
    points: list[tuple[dt.date, Decimal | None]],
    origin_date: dt.date,
    publication_lag_days: int,
    frequency: str,
) -> list[tuple[dt.date, Decimal | None]]:
    """Drop points whose publication date is after ``origin_date``."""
    return [
        (d, v)
        for d, v in points
        if _publication_date(d, publication_lag_days, frequency) <= origin_date
    ]


def build_dataset(
    session: Session,
    origin_date: dt.date,
    horizon: int = 0,
    lags: tuple[int, ...] = DEFAULT_LAGS,
) -> DatasetBundle:
    """Build a real-time dataset frozen at ``origin_date``.

    Pulls observations from the database for every registered series, trims
    them with each series' publication lag and assembles a monthly panel
    with lagged features. The target is the IPCA m/m value for
    ``month_start(origin_date) + horizon`` months.
    """
    if horizon < 0:
        raise ValueError("horizon must be >= 0")

    series_rows = list(session.query(Series).order_by(Series.code).all())
    if not series_rows:
        raise RuntimeError("No series registered — run `macro seed --fixtures` first.")

    monthly_series: dict[str, pd.Series] = {}
    cutoffs: dict[str, dt.date | None] = {}
    for s in series_rows:
        obs = (
            session.query(Observation)
            .filter(Observation.series_id == s.id)
            .order_by(Observation.reference_date)
            .all()
        )
        raw: list[tuple[dt.date, Decimal | None]] = [(o.reference_date, o.value) for o in obs]
        trimmed = _clip_to_origin(raw, origin_date, s.publication_lag_days, s.frequency)
        cutoffs[s.code] = trimmed[-1][0] if trimmed else None
        monthly_series[s.code] = _to_monthly(trimmed, s.frequency)

    index = _common_monthly_index(monthly_series)
    if len(index) == 0:
        raise RuntimeError(f"No usable observations before {origin_date}.")

    features = pd.DataFrame(index=index)
    for code, series in monthly_series.items():
        aligned = series.reindex(index)
        for lag in lags:
            features[f"{code}__lag{lag}"] = aligned.shift(lag)
    features.index.name = "ds"

    target_month = _month_start(origin_date) + relativedelta(months=horizon)
    target_series = monthly_series.get(TARGET_CODE, pd.Series(dtype="float64"))
    target_series = target_series.reindex(index).rename("y")
    target_series.index.name = "ds"

    return DatasetBundle(
        features=features,
        target=target_series,
        origin_date=origin_date,
        horizon=horizon,
        target_month=target_month,
        asof_cutoffs=cutoffs,
    )


def _common_monthly_index(series_map: dict[str, pd.Series]) -> pd.DatetimeIndex:
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    for s in series_map.values():
        if len(s):
            starts.append(s.index.min())
            ends.append(s.index.max())
    if not starts:
        return pd.DatetimeIndex([])
    start = min(starts)
    end = max(ends)
    return pd.date_range(start=start, end=end, freq="MS")
