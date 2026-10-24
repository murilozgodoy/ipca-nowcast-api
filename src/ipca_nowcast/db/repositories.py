"""Repositories encapsulate persistence operations.

Portable upserts: we detect the dialect and use the vendor-specific
`INSERT ... ON CONFLICT ...` for Postgres and SQLite (both supported by
SQLAlchemy 2.0). Other dialects fall back to a merge pattern.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ipca_nowcast.db.models import (
    BacktestResult,
    FocusExpectation,
    Forecast,
    IngestionRun,
    Observation,
    Series,
)

_UPSERT_BATCH_SIZE = 1000


def _upsert(
    session: Session,
    table: Any,
    rows: list[dict[str, Any]],
    conflict_columns: list[str],
    update_columns: list[str],
) -> int:
    """Portable UPSERT. Chunks the input to stay under Postgres's 65 535
    parameter cap per statement. Returns rowcount (best-effort)."""
    if not rows:
        return 0
    dialect = session.get_bind().dialect.name
    if dialect in ("postgresql", "sqlite"):
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            dialect_insert: Any = pg_insert
        else:
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            dialect_insert = sqlite_insert

        total = 0
        for start in range(0, len(rows), _UPSERT_BATCH_SIZE):
            chunk = rows[start : start + _UPSERT_BATCH_SIZE]
            stmt: Any = dialect_insert(table).values(chunk)
            set_map = {c: getattr(stmt.excluded, c) for c in update_columns}
            stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=set_map)
            result: Any = session.execute(stmt)
            count = getattr(result, "rowcount", None)
            total += int(count) if count and count > 0 else len(chunk)
        return total
    # Fallback: merge row-by-row.
    affected = 0
    for row in rows:
        session.merge(table(**row))
        affected += 1
    return affected


class SeriesRepository:
    """Metadata registry for macro series."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, series: Iterable[Mapping[str, Any]]) -> int:
        rows = [dict(s) for s in series]
        if not rows:
            return 0
        return _upsert(
            self.session,
            Series,
            rows,
            conflict_columns=["code"],
            update_columns=[
                "external_id",
                "source",
                "name",
                "unit",
                "frequency",
                "publication_lag_days",
                "is_target",
            ],
        )

    def get_by_code(self, code: str) -> Series | None:
        return self.session.scalars(select(Series).where(Series.code == code)).first()

    def list_all(self) -> list[Series]:
        return list(self.session.scalars(select(Series).order_by(Series.code)))


class ObservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, series_id: int, points: Iterable[tuple[dt.date, Decimal | None]]) -> int:
        rows = [
            {"series_id": series_id, "reference_date": d, "value": v}
            for d, v in points
            if d is not None
        ]
        return _upsert(
            self.session,
            Observation,
            rows,
            conflict_columns=["series_id", "reference_date"],
            update_columns=["value"],
        )

    def list_for_series(self, series_id: int, until: dt.date | None = None) -> list[Observation]:
        stmt = select(Observation).where(Observation.series_id == series_id)
        if until is not None:
            stmt = stmt.where(Observation.reference_date <= until)
        stmt = stmt.order_by(Observation.reference_date)
        return list(self.session.scalars(stmt))


class FocusRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: Iterable[Mapping[str, Any]]) -> int:
        rows_list = [dict(r) for r in rows]
        return _upsert(
            self.session,
            FocusExpectation,
            rows_list,
            conflict_columns=["indicator", "reference_date", "collected_at", "base_calculo"],
            update_columns=["median", "mean", "std_dev", "n_respondents"],
        )


class ForecastRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: Iterable[Mapping[str, Any]]) -> int:
        rows_list = [dict(r) for r in rows]
        return _upsert(
            self.session,
            Forecast,
            rows_list,
            conflict_columns=["model", "origin_date", "reference_date", "horizon"],
            update_columns=["prediction", "pi_lower", "pi_upper"],
        )


class BacktestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: Iterable[Mapping[str, Any]]) -> int:
        rows_list = [dict(r) for r in rows]
        return _upsert(
            self.session,
            BacktestResult,
            rows_list,
            conflict_columns=["model", "horizon", "subperiod"],
            update_columns=[
                "n",
                "rmse",
                "mae",
                "bias",
                "rmse_vs_focus",
                "dm_stat_vs_focus",
                "dm_pvalue_vs_focus",
            ],
        )


class IngestionRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(self, kind: str, message: str | None = None) -> IngestionRun:
        run = IngestionRun(kind=kind, status="running", message=message)
        self.session.add(run)
        self.session.flush()
        return run

    def finish(
        self,
        run: IngestionRun,
        status: str,
        rows_affected: int | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        run.status = status
        run.rows_affected = rows_affected
        run.message = message
        run.details = details
        run.finished_at = dt.datetime.now(dt.UTC)
        self.session.add(run)
