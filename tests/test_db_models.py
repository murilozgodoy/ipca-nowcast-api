"""Smoke tests for the SQLAlchemy models against an in-memory SQLite DB."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ipca_nowcast.db.base import Base
from ipca_nowcast.db.models import Observation, Series
from ipca_nowcast.db.repositories import (
    FocusRepository,
    ForecastRepository,
    IngestionRunRepository,
    ObservationRepository,
    SeriesRepository,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_create_series_and_observation(session: Session) -> None:
    s = Series(
        code="sgs.433",
        external_id="433",
        source="BCB_SGS",
        name="IPCA mensal",
        unit="pct_month",
        frequency="monthly",
        publication_lag_days=11,
        is_target=True,
    )
    session.add(s)
    session.flush()
    session.add(
        Observation(series_id=s.id, reference_date=dt.date(2024, 10, 1), value=Decimal("0.56"))
    )
    session.commit()
    assert s.id is not None
    assert len(s.observations) == 1


def test_series_upsert_is_idempotent(session: Session) -> None:
    repo = SeriesRepository(session)
    row = {
        "code": "sgs.433",
        "external_id": "433",
        "source": "BCB_SGS",
        "name": "IPCA mensal",
        "unit": "pct_month",
        "frequency": "monthly",
        "publication_lag_days": 11,
        "is_target": True,
    }
    repo.upsert_many([row])
    repo.upsert_many([{**row, "name": "IPCA — variação mensal"}])
    session.commit()
    all_series = repo.list_all()
    assert len(all_series) == 1
    assert all_series[0].name == "IPCA — variação mensal"


def test_observation_upsert_overwrites_value(session: Session) -> None:
    series_repo = SeriesRepository(session)
    obs_repo = ObservationRepository(session)
    series_repo.upsert_many(
        [
            {
                "code": "sgs.433",
                "external_id": "433",
                "source": "BCB_SGS",
                "name": "IPCA",
                "unit": "pct",
                "frequency": "monthly",
                "publication_lag_days": 11,
                "is_target": True,
            }
        ]
    )
    session.commit()
    sid = series_repo.get_by_code("sgs.433").id  # type: ignore[union-attr]
    obs_repo.upsert_many(sid, [(dt.date(2024, 10, 1), Decimal("0.50"))])
    obs_repo.upsert_many(sid, [(dt.date(2024, 10, 1), Decimal("0.56"))])
    session.commit()
    rows = obs_repo.list_for_series(sid)
    assert len(rows) == 1
    assert rows[0].value == Decimal("0.56")


def test_focus_and_forecast_repos_upsert(session: Session) -> None:
    f_repo = FocusRepository(session)
    f_repo.upsert_many(
        [
            {
                "indicator": "IPCA",
                "reference_date": dt.date(2024, 11, 1),
                "collected_at": dt.date(2024, 10, 25),
                "base_calculo": 0,
                "median": Decimal("0.39"),
                "mean": Decimal("0.40"),
                "std_dev": Decimal("0.05"),
                "n_respondents": 61,
            }
        ]
    )
    fc_repo = ForecastRepository(session)
    fc_repo.upsert_many(
        [
            {
                "model": "SARIMA",
                "origin_date": dt.date(2024, 10, 25),
                "reference_date": dt.date(2024, 11, 1),
                "horizon": 0,
                "prediction": Decimal("0.45"),
            }
        ]
    )
    session.commit()


def test_ingestion_run_lifecycle(session: Session) -> None:
    repo = IngestionRunRepository(session)
    run = repo.start("ingest-all")
    repo.finish(run, status="ok", rows_affected=42, message="done", details={"series": 7})
    session.commit()
    assert run.status == "ok"
    assert run.rows_affected == 42
