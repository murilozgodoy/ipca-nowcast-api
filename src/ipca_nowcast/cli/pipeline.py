"""`macro nowcast` and `macro backtest` subcommands."""

from __future__ import annotations

import datetime as dt
import json

import typer

from ipca_nowcast.config import get_settings
from ipca_nowcast.db.session import session_scope
from ipca_nowcast.evaluation.backtest import BacktestConfig, persist_backtest, run_backtest
from ipca_nowcast.features.dataset import build_dataset
from ipca_nowcast.logging import configure_logging
from ipca_nowcast.models.base import Forecaster
from ipca_nowcast.models.baselines import FocusBaseline, HistoricalMean, RandomWalk, SeasonalNaive
from ipca_nowcast.models.combo import MeanCombination
from ipca_nowcast.models.sarima import SarimaForecaster
from ipca_nowcast.models.sklearn_models import ElasticNetForecaster, GradientBoostingForecaster


def _build_forecasters(session) -> list[Forecaster]:
    base: list[Forecaster] = [
        RandomWalk(),
        HistoricalMean(window=12),
        SeasonalNaive(),
        FocusBaseline(session=session),
        ElasticNetForecaster(),
        SarimaForecaster(),
        GradientBoostingForecaster(),
    ]
    combo = MeanCombination(
        components=[
            base[4],  # ElasticNet
            base[5],  # SARIMA
            base[6],  # GBM
        ],
        name="combo_mean",
    )
    return [*base, combo]


def register(app: typer.Typer) -> None:
    @app.command()
    def nowcast(
        origin: str = typer.Option(None, help="Origin date (YYYY-MM-DD); defaults to today."),
        horizon: int = typer.Option(0, help="Horizon in months (0 = current month)."),
    ) -> None:
        """Produce a nowcast for the IPCA using every registered model."""
        configure_logging(get_settings().log_level)
        origin_date = dt.date.fromisoformat(origin) if origin else dt.date.today()
        with session_scope() as session:
            forecasters = _build_forecasters(session)
            bundle = build_dataset(session, origin_date=origin_date, horizon=horizon)
            results = {f.name: f.predict(bundle).__dict__ for f in forecasters}
        typer.echo(
            json.dumps(
                {
                    "origin_date": origin_date.isoformat(),
                    "horizon": horizon,
                    "target_month": bundle.target_month.isoformat(),
                    "models": results,
                },
                indent=2,
                default=str,
            )
        )

    @app.command()
    def backtest(
        start: str = typer.Option("2018-01-15"),
        end: str | None = typer.Option(None),
        horizons: str = typer.Option("0,1,2,3", help="Comma-separated horizons."),
        persist: bool = typer.Option(True, help="Save results to the database."),
    ) -> None:
        """Run the expanding-window backtest and (optionally) persist results."""
        configure_logging(get_settings().log_level)
        cfg = BacktestConfig(
            start=dt.date.fromisoformat(start),
            end=dt.date.fromisoformat(end) if end else None,
            horizons=tuple(int(x) for x in horizons.split(",")),
        )
        with session_scope() as session:
            forecasters = _build_forecasters(session)
            output = run_backtest(session, forecasters, cfg)
            if persist:
                counts = persist_backtest(session, output)
                typer.echo(f"persisted: {counts}")
        typer.echo(
            json.dumps(
                {"forecasts": len(output.forecasts), "metrics": len(output.metrics)},
                indent=2,
            )
        )
