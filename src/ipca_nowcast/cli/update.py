"""`macro update` and `macro export-fixtures` CLI subcommands.

`update` runs the end-to-end daily pipeline: ingest the registry, fetch
every series + Focus, produce a nowcast, persist everything, and record a
row in ``ingestion_runs``.

`export-fixtures` renders the live API responses to a folder of JSON
files consumed by the Mock Service Worker in `ipca-nowcast-web/`.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import typer
from fastapi.testclient import TestClient

from ipca_nowcast.api.main import app
from ipca_nowcast.config import get_settings
from ipca_nowcast.db.repositories import IngestionRunRepository
from ipca_nowcast.db.session import session_scope
from ipca_nowcast.evaluation.backtest import BacktestConfig, persist_backtest, run_backtest
from ipca_nowcast.features.dataset import build_dataset
from ipca_nowcast.ingestion.service import IngestionService
from ipca_nowcast.logging import configure_logging, get_logger
from ipca_nowcast.models.base import Forecaster
from ipca_nowcast.models.baselines import FocusBaseline, HistoricalMean, RandomWalk, SeasonalNaive
from ipca_nowcast.models.combo import MeanCombination
from ipca_nowcast.models.sarima import SarimaForecaster
from ipca_nowcast.models.sklearn_models import ElasticNetForecaster, GradientBoostingForecaster

_logger = get_logger(__name__)


def register(app_cli: typer.Typer) -> None:
    @app_cli.command()
    def update(
        skip_ingest: bool = typer.Option(False, help="Skip remote ingestion."),
        skip_focus: bool = typer.Option(False, help="Skip Focus ingestion."),
        skip_backtest: bool = typer.Option(True, help="Skip the full backtest."),
        use_cache: bool = typer.Option(True, help="Reuse cached raw downloads."),
    ) -> None:
        """Run the end-to-end pipeline: ingest -> nowcast -> persist."""
        configure_logging(get_settings().log_level)
        with session_scope() as session:
            runs = IngestionRunRepository(session)
            run = runs.start("update")
            try:
                svc = IngestionService(session)
                details: dict[str, object] = {}
                if not skip_ingest:
                    outcomes = svc.ingest_all(use_cache=use_cache)
                    details["series"] = {o.series_code: o.rows_upserted for o in outcomes}
                if not skip_focus:
                    details["focus_rows"] = svc.ingest_focus(use_cache=use_cache)
                origin = dt.date.today()
                bundle = build_dataset(session, origin_date=origin, horizon=0)
                forecasters: list[Forecaster] = [
                    RandomWalk(),
                    HistoricalMean(window=12),
                    SeasonalNaive(),
                    FocusBaseline(session),
                    ElasticNetForecaster(),
                    SarimaForecaster(),
                    GradientBoostingForecaster(),
                ]
                combo = MeanCombination(components=list(forecasters[-3:]), name="combo_mean")
                for f in [*forecasters, combo]:
                    f.predict(bundle)
                if not skip_backtest:
                    cfg = BacktestConfig(start=dt.date(2015, 1, 15))
                    output = run_backtest(session, [*forecasters, combo], cfg)
                    persist_backtest(session, output)
                    details["backtest_rows"] = len(output.metrics)
                runs.finish(run, status="ok", message="pipeline ok", details=details)
            except Exception as exc:
                runs.finish(run, status="error", message=str(exc))
                raise
        typer.echo("update ok")

    @app_cli.command("export-fixtures")
    def export_fixtures(
        output: Path = typer.Option(
            Path("../ipca-nowcast-web/src/mocks/fixtures"),
            help="Target directory (will be created).",
        ),
    ) -> None:
        """Export live API responses as JSON files to the frontend's MSW folder."""
        configure_logging(get_settings().log_level)
        output.mkdir(parents=True, exist_ok=True)
        client = TestClient(app)
        endpoints = {
            "health": "/health",
            "series": "/series",
            "series_sgs433": "/series/sgs.433",
            "nowcast_latest_h0": "/nowcast/latest?horizon=0",
            "nowcast_latest_h1": "/nowcast/latest?horizon=1",
            "backtest_metrics": "/backtest/metrics",
            "backtest_forecasts": "/backtest/forecasts?limit=500",
            "focus_latest": "/focus/latest?limit=12",
            "ipca_groups": "/ipca/groups",
        }
        for name, path in endpoints.items():
            r = client.get(path)
            target = output / f"{name}.json"
            if r.status_code == 200:
                target.write_text(
                    json.dumps(r.json(), ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
                typer.echo(f"wrote {target.name}")
            else:
                typer.echo(f"skipped {path}: {r.status_code}")
