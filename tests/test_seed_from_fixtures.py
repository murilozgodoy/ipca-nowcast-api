"""End-to-end test for `IngestionService.seed_from_fixtures` on SQLite."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ipca_nowcast.db.base import Base
from ipca_nowcast.ingestion.service import IngestionService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_seed_from_fixtures_populates_db(session: Session, fixtures_dir: Path) -> None:
    svc = IngestionService(session)
    counts = svc.seed_from_fixtures(fixtures_dir)
    session.commit()
    assert counts["series"] >= 4
    assert counts.get("observations", 0) >= 4
    assert counts.get("focus_rows", 0) >= 1
