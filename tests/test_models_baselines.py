"""Tests for baseline forecasters."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ipca_nowcast.db.base import Base
from ipca_nowcast.features.dataset import build_dataset
from ipca_nowcast.ingestion.service import IngestionService
from ipca_nowcast.models.baselines import (
    FocusBaseline,
    HistoricalMean,
    RandomWalk,
    SeasonalNaive,
)
from ipca_nowcast.models.combo import MeanCombination


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


def test_random_walk_uses_last_target(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15))
    pred = RandomWalk().predict(bundle)
    # Last known IPCA at 2024-11-15 (with 11-day monthly lag) is Oct 2024 = 0.56
    assert pred.value == pytest.approx(0.56, abs=1e-6)


def test_historical_mean(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15))
    pred = HistoricalMean(window=12).predict(bundle)
    assert isinstance(pred.value, float)


def test_seasonal_naive_prefers_same_month_last_year(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15))
    pred = SeasonalNaive().predict(bundle)
    # target_month = Nov 2024, same month last year = Nov 2023 = 0.28
    assert pred.value == pytest.approx(0.28, abs=1e-6)


def test_focus_baseline_uses_latest_median_at_origin(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 10, 20), horizon=1)
    pred = FocusBaseline(seeded_session).predict(bundle)
    # Fixture has Nov 2024 medians collected on 2024-10-01, 2024-10-15 and
    # 2024-10-25. The most recent one on/before origin 2024-10-20 is 0.41.
    assert bundle.target_month == dt.date(2024, 11, 1)
    assert pred.value == pytest.approx(0.41, abs=1e-6)


def test_focus_baseline_falls_back_when_no_data_available(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 10, 20), horizon=3)
    # Horizon 3 => target month = Jan 2025; only one Focus row for Jan 2025 in fixture.
    pred = FocusBaseline(seeded_session).predict(bundle)
    # Collected 2024-10-25 > origin 2024-10-20, so falls back to RW last value.
    assert isinstance(pred.value, float)


def test_combo_averages_components(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15))
    combo = MeanCombination(components=[RandomWalk(), SeasonalNaive(), HistoricalMean(window=12)])
    pred = combo.predict(bundle)
    assert isinstance(pred.value, float)


# Silence unused import.
_ = Decimal
