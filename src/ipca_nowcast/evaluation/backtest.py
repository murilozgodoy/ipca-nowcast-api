"""Expanding-window backtest comparing models against the Focus benchmark."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from ipca_nowcast.db.models import Observation, Series
from ipca_nowcast.db.repositories import BacktestRepository, ForecastRepository
from ipca_nowcast.evaluation.dm_test import diebold_mariano
from ipca_nowcast.evaluation.metrics import bias, mae, rmse
from ipca_nowcast.features.dataset import TARGET_CODE, build_dataset
from ipca_nowcast.logging import get_logger
from ipca_nowcast.models.base import Forecaster

_logger = get_logger(__name__)

SUBPERIODS: dict[str, tuple[dt.date, dt.date]] = {
    "pre_2020": (dt.date(2000, 1, 1), dt.date(2019, 12, 31)),
    "pandemic": (dt.date(2020, 1, 1), dt.date(2021, 12, 31)),
    "post_2022": (dt.date(2022, 1, 1), dt.date(2100, 12, 31)),
}


@dataclass
class ForecastRow:
    model: str
    origin_date: dt.date
    reference_date: dt.date
    horizon: int
    prediction: float
    actual: float | None
    pi_lower: float | None = None
    pi_upper: float | None = None


@dataclass
class BacktestConfig:
    start: dt.date = dt.date(2018, 1, 15)
    end: dt.date | None = None
    horizons: tuple[int, ...] = (0, 1, 2, 3)
    cadence: str = "monthly"
    focus_model_name: str = "focus_median"


@dataclass
class BacktestOutput:
    forecasts: list[ForecastRow]
    metrics: list[dict[str, object]]
    config: BacktestConfig = field(default_factory=BacktestConfig)


def _target_actuals(session: Session) -> dict[dt.date, float]:
    s = session.query(Series).filter(Series.code == TARGET_CODE).first()
    if s is None:
        return {}
    rows = (
        session.query(Observation)
        .filter(Observation.series_id == s.id)
        .order_by(Observation.reference_date)
        .all()
    )
    out: dict[dt.date, float] = {}
    for r in rows:
        if r.value is not None:
            out[dt.date(r.reference_date.year, r.reference_date.month, 1)] = float(r.value)
    return out


def _iter_origins(cfg: BacktestConfig) -> Iterable[dt.date]:
    end = cfg.end or dt.date.today()
    current = cfg.start
    while current <= end:
        yield current
        current += relativedelta(months=1)


def run_backtest(
    session: Session,
    forecasters: list[Forecaster],
    config: BacktestConfig | None = None,
) -> BacktestOutput:
    """Run the expanding-window backtest and return raw predictions + metrics."""
    cfg = config or BacktestConfig()
    actuals = _target_actuals(session)
    forecasts: list[ForecastRow] = []

    for origin in _iter_origins(cfg):
        for horizon in cfg.horizons:
            try:
                bundle = build_dataset(session, origin_date=origin, horizon=horizon)
            except RuntimeError:
                continue
            for forecaster in forecasters:
                try:
                    pred = forecaster.predict(bundle)
                except Exception as exc:
                    _logger.warning(
                        "forecaster_failed", model=forecaster.name, origin=origin, error=str(exc)
                    )
                    continue
                ref_month = bundle.target_month
                forecasts.append(
                    ForecastRow(
                        model=forecaster.name,
                        origin_date=origin,
                        reference_date=ref_month,
                        horizon=horizon,
                        prediction=float(pred.value),
                        actual=actuals.get(ref_month),
                        pi_lower=pred.pi_lower,
                        pi_upper=pred.pi_upper,
                    )
                )

    metrics = compute_metrics(forecasts, focus_model_name=cfg.focus_model_name)
    return BacktestOutput(forecasts=forecasts, metrics=metrics, config=cfg)


def _subperiod_label(d: dt.date) -> list[str]:
    out = ["full"]
    for label, (s, e) in SUBPERIODS.items():
        if s <= d <= e:
            out.append(label)
    return out


def compute_metrics(
    forecasts: list[ForecastRow],
    focus_model_name: str = "focus_median",
) -> list[dict[str, object]]:
    """Aggregate RMSE/MAE/bias per (model, horizon, subperiod) + DM vs. Focus."""
    df = pd.DataFrame([f.__dict__ for f in forecasts])
    if df.empty:
        return []
    df = df.dropna(subset=["actual"]).copy()
    df["error"] = df["prediction"] - df["actual"]
    rows: list[dict[str, object]] = []
    for group_key, sub in df.groupby(["model", "horizon"]):
        model_name = str(group_key[0])  # type: ignore[index]
        horizon_int = int(group_key[1])  # type: ignore[index,arg-type,call-overload]
        for label in ("full", *SUBPERIODS.keys()):
            if label == "full":
                mask = pd.Series(True, index=sub.index)
            else:
                s, e = SUBPERIODS[label]
                mask = (sub["reference_date"] >= s) & (sub["reference_date"] <= e)
            scope = sub.loc[mask]
            if scope.empty:
                continue
            errs = scope["error"].tolist()
            rmse_val = rmse(errs)
            # DM test against Focus on the same (horizon, scope) rows
            focus_scope = df[
                (df["model"] == focus_model_name)
                & (df["horizon"] == horizon_int)
                & (df["reference_date"].isin(scope["reference_date"]))
            ].set_index("reference_date")["error"]
            aligned = scope.set_index("reference_date")
            common = aligned.index.intersection(focus_scope.index)
            dm_stat = float("nan")
            dm_p = float("nan")
            rmse_focus = float("nan")
            if len(common) >= 10 and model_name != focus_model_name:
                a = aligned.loc[common, "error"].tolist()
                b = focus_scope.loc[common].tolist()
                dm = diebold_mariano(a, b, h=max(1, horizon_int + 1))
                dm_stat = dm.dm_stat
                dm_p = dm.p_value
                rmse_focus = rmse(b)
            rows.append(
                {
                    "model": model_name,
                    "horizon": horizon_int,
                    "subperiod": label,
                    "n": len(scope),
                    "rmse": rmse_val,
                    "mae": mae(errs),
                    "bias": bias(errs),
                    "rmse_vs_focus": (rmse_val / rmse_focus)
                    if rmse_focus and not math.isnan(rmse_focus)
                    else None,
                    "dm_stat_vs_focus": None if math.isnan(dm_stat) else dm_stat,
                    "dm_pvalue_vs_focus": None if math.isnan(dm_p) else dm_p,
                }
            )
    return rows


def persist_backtest(session: Session, output: BacktestOutput) -> dict[str, int]:
    """Write forecasts and metrics back to the database."""
    fc_repo = ForecastRepository(session)
    bt_repo = BacktestRepository(session)
    fc_rows = [
        {
            "model": f.model,
            "origin_date": f.origin_date,
            "reference_date": f.reference_date,
            "horizon": int(f.horizon),
            "prediction": Decimal(str(f.prediction)),
            "pi_lower": Decimal(str(f.pi_lower)) if f.pi_lower is not None else None,
            "pi_upper": Decimal(str(f.pi_upper)) if f.pi_upper is not None else None,
        }
        for f in output.forecasts
    ]
    n_fc = fc_repo.upsert_many(fc_rows)
    metric_rows = []
    for m in output.metrics:
        metric_rows.append(
            {
                "model": m["model"],
                "horizon": m["horizon"],
                "subperiod": m["subperiod"],
                "n": m["n"],
                "rmse": _dec(m.get("rmse")),
                "mae": _dec(m.get("mae")),
                "bias": _dec(m.get("bias")),
                "rmse_vs_focus": _dec(m.get("rmse_vs_focus")),
                "dm_stat_vs_focus": _dec(m.get("dm_stat_vs_focus")),
                "dm_pvalue_vs_focus": _dec(m.get("dm_pvalue_vs_focus")),
            }
        )
    n_bt = bt_repo.upsert_many(metric_rows)
    return {"forecasts": int(n_fc), "backtest_rows": int(n_bt)}


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return Decimal(str(round(f, 8)))
