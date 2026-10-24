"""HTTP endpoints — thin layer over repositories and the pipeline."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ipca_nowcast import __version__
from ipca_nowcast.api.dependencies import db_session
from ipca_nowcast.api.schemas import (
    BacktestMetric,
    FocusLatestPoint,
    ForecastPoint,
    Health,
    IpcaGroupPoint,
    NowcastLatest,
    NowcastRow,
    Observation,
    SeriesDetail,
    SeriesOut,
)
from ipca_nowcast.db.models import (
    BacktestResult,
    FocusExpectation,
    Forecast,
    Series,
)
from ipca_nowcast.db.models import (
    Observation as DbObservation,
)
from ipca_nowcast.features.dataset import build_dataset
from ipca_nowcast.ingestion.sidra import SidraClient
from ipca_nowcast.models.baselines import FocusBaseline, HistoricalMean, RandomWalk, SeasonalNaive
from ipca_nowcast.models.combo import MeanCombination
from ipca_nowcast.models.sarima import SarimaForecaster
from ipca_nowcast.models.sklearn_models import ElasticNetForecaster, GradientBoostingForecaster

router = APIRouter()


@router.get("/health", response_model=Health, tags=["meta"])
def health(session: Session = Depends(db_session)) -> Health:
    db_status: str = "up"
    try:
        session.execute(select(1))
    except Exception:
        db_status = "down"
    return Health(
        status="ok" if db_status == "up" else "degraded",
        version=__version__,
        database=db_status,  # type: ignore[arg-type]
    )


@router.get("/series", response_model=list[SeriesOut], tags=["series"])
def list_series(session: Session = Depends(db_session)) -> list[SeriesOut]:
    rows = session.scalars(select(Series).order_by(Series.code)).all()
    return [SeriesOut.model_validate(r) for r in rows]


@router.get("/series/{code}", response_model=SeriesDetail, tags=["series"])
def get_series(
    code: str,
    session: Session = Depends(db_session),
    start: dt.date | None = Query(default=None),
    end: dt.date | None = Query(default=None),
) -> SeriesDetail:
    series = session.scalars(select(Series).where(Series.code == code)).first()
    if series is None:
        raise HTTPException(status_code=404, detail=f"Series '{code}' not found.")
    stmt = select(DbObservation).where(DbObservation.series_id == series.id)
    if start:
        stmt = stmt.where(DbObservation.reference_date >= start)
    if end:
        stmt = stmt.where(DbObservation.reference_date <= end)
    stmt = stmt.order_by(DbObservation.reference_date)
    obs = session.scalars(stmt).all()
    observations = [
        Observation(
            reference_date=o.reference_date, value=float(o.value) if o.value is not None else None
        )
        for o in obs
    ]
    base = SeriesOut.model_validate(series).model_dump()
    return SeriesDetail(
        **base,
        first_date=observations[0].reference_date if observations else None,
        last_date=observations[-1].reference_date if observations else None,
        n=len(observations),
        observations=observations,
    )


@router.get("/nowcast/latest", response_model=NowcastLatest, tags=["nowcast"])
def nowcast_latest(
    session: Session = Depends(db_session),
    horizon: int = Query(default=0, ge=0, le=3),
    origin: dt.date | None = Query(default=None),
) -> NowcastLatest:
    origin_date = origin or dt.date.today()
    bundle = build_dataset(session, origin_date=origin_date, horizon=horizon)
    from ipca_nowcast.models.base import Forecaster

    forecasters: list[Forecaster] = [
        RandomWalk(),
        HistoricalMean(window=12),
        SeasonalNaive(),
        ElasticNetForecaster(),
        SarimaForecaster(),
        GradientBoostingForecaster(),
    ]
    combo = MeanCombination(components=list(forecasters[-3:]), name="combo_mean")
    focus = FocusBaseline(session=session)
    rows: list[NowcastRow] = []
    for f in [*forecasters, combo]:
        p = f.predict(bundle)
        rows.append(
            NowcastRow(model=p.model, prediction=p.value, pi_lower=p.pi_lower, pi_upper=p.pi_upper)
        )
    focus_pred = focus.predict(bundle).value
    return NowcastLatest(
        origin_date=bundle.origin_date,
        target_month=bundle.target_month,
        horizon=horizon,
        models=rows,
        focus_median=focus_pred,
    )


@router.get("/backtest/metrics", response_model=list[BacktestMetric], tags=["backtest"])
def backtest_metrics(
    session: Session = Depends(db_session),
    horizon: int | None = Query(default=None, ge=0, le=3),
    subperiod: str | None = Query(default=None),
) -> list[BacktestMetric]:
    stmt = select(BacktestResult)
    if horizon is not None:
        stmt = stmt.where(BacktestResult.horizon == horizon)
    if subperiod:
        stmt = stmt.where(BacktestResult.subperiod == subperiod)
    stmt = stmt.order_by(BacktestResult.horizon, BacktestResult.model)
    rows = session.scalars(stmt).all()
    out: list[BacktestMetric] = []
    for r in rows:
        out.append(
            BacktestMetric(
                model=r.model,
                horizon=r.horizon,
                subperiod=r.subperiod,
                n=r.n,
                rmse=float(r.rmse) if r.rmse is not None else None,
                mae=float(r.mae) if r.mae is not None else None,
                bias=float(r.bias) if r.bias is not None else None,
                rmse_vs_focus=float(r.rmse_vs_focus) if r.rmse_vs_focus is not None else None,
                dm_stat_vs_focus=float(r.dm_stat_vs_focus)
                if r.dm_stat_vs_focus is not None
                else None,
                dm_pvalue_vs_focus=float(r.dm_pvalue_vs_focus)
                if r.dm_pvalue_vs_focus is not None
                else None,
            )
        )
    return out


@router.get("/backtest/forecasts", response_model=list[ForecastPoint], tags=["backtest"])
def backtest_forecasts(
    session: Session = Depends(db_session),
    model: str | None = Query(default=None),
    horizon: int | None = Query(default=None, ge=0, le=3),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> list[ForecastPoint]:
    stmt = select(Forecast)
    if model:
        stmt = stmt.where(Forecast.model == model)
    if horizon is not None:
        stmt = stmt.where(Forecast.horizon == horizon)
    stmt = stmt.order_by(Forecast.reference_date.desc(), Forecast.model).limit(limit).offset(offset)
    rows = session.scalars(stmt).all()
    return [
        ForecastPoint(
            model=r.model,
            origin_date=r.origin_date,
            reference_date=r.reference_date,
            horizon=r.horizon,
            prediction=float(r.prediction),
            pi_lower=float(r.pi_lower) if r.pi_lower is not None else None,
            pi_upper=float(r.pi_upper) if r.pi_upper is not None else None,
        )
        for r in rows
    ]


@router.get("/ipca/groups", response_model=list[IpcaGroupPoint], tags=["ipca"])
def ipca_groups(
    start: dt.date | None = Query(default=None),
    end: dt.date | None = Query(default=None),
) -> list[IpcaGroupPoint]:
    """Monthly IPCA variation by top-level group (table 7060 at IBGE SIDRA).

    Fetched live from ``apisidra.ibge.gov.br`` with on-disk caching through
    ``HttpClient``. Returns an empty list if the upstream service fails.
    """
    try:
        client = SidraClient()
        points = client.fetch_ipca_groups(start=start, end=end, use_cache=True)
    except Exception:
        return []
    out: list[IpcaGroupPoint] = []
    for p in points:
        out.append(
            IpcaGroupPoint(
                reference_date=p.reference_date,
                group_code=p.group_code,
                group_name=p.group_name,
                monthly_pct=float(p.monthly_pct) if p.monthly_pct is not None else None,
            )
        )
    if start:
        out = [p for p in out if p.reference_date >= start]
    if end:
        out = [p for p in out if p.reference_date <= end]
    return out


@router.get("/focus/latest", response_model=list[FocusLatestPoint], tags=["focus"])
def focus_latest(
    session: Session = Depends(db_session),
    reference_date: dt.date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[FocusLatestPoint]:
    """Latest Focus median per reference month (one row per month)."""
    sub_stmt = (
        select(
            FocusExpectation.reference_date,
            func.max(FocusExpectation.collected_at).label("collected_at"),
        )
        .where(FocusExpectation.indicator == "IPCA")
        .where(FocusExpectation.base_calculo == 0)
    )
    if reference_date is not None:
        sub_stmt = sub_stmt.where(FocusExpectation.reference_date == reference_date)
    sub = sub_stmt.group_by(FocusExpectation.reference_date).subquery()

    stmt = (
        select(FocusExpectation)
        .join(
            sub,
            (FocusExpectation.reference_date == sub.c.reference_date)
            & (FocusExpectation.collected_at == sub.c.collected_at),
        )
        .where(FocusExpectation.indicator == "IPCA")
        .where(FocusExpectation.base_calculo == 0)
        .order_by(FocusExpectation.reference_date.desc())
        .limit(limit)
    )
    rows = session.scalars(stmt).all()
    return [
        FocusLatestPoint(
            reference_date=r.reference_date,
            collected_at=r.collected_at,
            median=float(r.median) if r.median is not None else None,
            mean=float(r.mean) if r.mean is not None else None,
            std_dev=float(r.std_dev) if r.std_dev is not None else None,
            n_respondents=r.n_respondents,
        )
        for r in rows
    ]
