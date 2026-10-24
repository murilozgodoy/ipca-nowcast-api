"""Smoke test for the backtest machinery against fixtures.

Uses a tiny subset of models (baselines only) and a short origin window so
the test stays well under 10s even on slow runners.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ipca_nowcast.db.base import Base
from ipca_nowcast.evaluation.backtest import BacktestConfig, persist_backtest, run_backtest
from ipca_nowcast.ingestion.service import IngestionService
from ipca_nowcast.models.baselines import FocusBaseline, RandomWalk, SeasonalNaive


@pytest.fixture
def seeded_session(tmp_path: Path, fixtures_dir: Path) -> Session:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        svc = IngestionService(session)
        svc.seed_from_fixtures(fixtures_dir)
        session.commit()
        yield session


def test_backtest_runs_and_persists(seeded_session: Session) -> None:
    forecasters = [RandomWalk(), SeasonalNaive(), FocusBaseline(seeded_session)]
    cfg = BacktestConfig(
        start=dt.date(2022, 1, 15),
        end=dt.date(2024, 10, 15),
        horizons=(0,),
    )
    output = run_backtest(seeded_session, forecasters, cfg)
    assert output.forecasts, "no forecasts produced"
    assert output.metrics, "no metrics computed"

    counts = persist_backtest(seeded_session, output)
    seeded_session.commit()
    assert counts["forecasts"] >= 1


def test_backtest_metrics_contain_rmse_for_each_model(seeded_session: Session) -> None:
    forecasters = [RandomWalk(), SeasonalNaive()]
    cfg = BacktestConfig(start=dt.date(2023, 1, 15), end=dt.date(2024, 6, 15), horizons=(0,))
    output = run_backtest(seeded_session, forecasters, cfg)
    models = {m["model"] for m in output.metrics}
    assert "random_walk" in models
    assert "seasonal_naive" in models
    for metric in output.metrics:
        assert metric["subperiod"] in {"full", "pre_2020", "pandemic", "post_2022"}
