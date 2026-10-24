"""TestClient tests for the FastAPI endpoints — seeded against SQLite."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ipca_nowcast.db.session as db_session_module
from ipca_nowcast.api.main import app
from ipca_nowcast.db.base import Base
from ipca_nowcast.evaluation.backtest import BacktestConfig, persist_backtest, run_backtest
from ipca_nowcast.ingestion.service import IngestionService
from ipca_nowcast.models.baselines import FocusBaseline, RandomWalk, SeasonalNaive


@pytest.fixture
def client(tmp_path: Path, fixtures_dir: Path) -> TestClient:
    db_path = tmp_path / "api.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    # Monkey-patch the module-level engine/sessionmaker so FastAPI dependency
    # resolves to this test database.
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db_session_module._engine = engine
    db_session_module._SessionLocal = SessionLocal

    with SessionLocal() as session:
        svc = IngestionService(session)
        svc.seed_from_fixtures(fixtures_dir)
        session.commit()

        # Seed backtest results against the fixture dataset so the API has
        # something to serve.
        forecasters = [RandomWalk(), SeasonalNaive(), FocusBaseline(session)]
        cfg = BacktestConfig(
            start=dt.date(2023, 6, 15),
            end=dt.date(2024, 9, 15),
            horizons=(0,),
        )
        output = run_backtest(session, forecasters, cfg)
        persist_backtest(session, output)
        session.commit()

    yield TestClient(app)
    db_session_module.reset_engine_for_tests()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


def test_list_series(client: TestClient) -> None:
    r = client.get("/series")
    assert r.status_code == 200
    body = r.json()
    assert any(s["code"] == "sgs.433" for s in body)


def test_get_series_detail(client: TestClient) -> None:
    r = client.get("/series/sgs.433")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "sgs.433"
    assert body["n"] >= 1
    assert body["observations"]


def test_get_series_404(client: TestClient) -> None:
    r = client.get("/series/does-not-exist")
    assert r.status_code == 404


def test_nowcast_latest(client: TestClient) -> None:
    r = client.get("/nowcast/latest?origin=2024-10-20&horizon=1")
    assert r.status_code == 200
    body = r.json()
    assert body["target_month"] == "2024-11-01"
    assert any(m["model"] == "random_walk" for m in body["models"])
    assert body["focus_median"] is not None


def test_backtest_metrics(client: TestClient) -> None:
    r = client.get("/backtest/metrics?horizon=0&subperiod=full")
    assert r.status_code == 200
    body = r.json()
    assert body
    assert all(m["horizon"] == 0 for m in body)


def test_backtest_forecasts_pagination(client: TestClient) -> None:
    r = client.get("/backtest/forecasts?limit=5&offset=0")
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_focus_latest(client: TestClient) -> None:
    r = client.get("/focus/latest?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body
    assert all("median" in row for row in body)
