"""Ingestion orchestration: fetch → validate → upsert."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from ipca_nowcast.config import get_settings
from ipca_nowcast.db.repositories import (
    FocusRepository,
    IngestionRunRepository,
    ObservationRepository,
    SeriesRepository,
)
from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.ingestion.focus import FocusClient
from ipca_nowcast.ingestion.quality import QualityReport, check_quality
from ipca_nowcast.ingestion.registry import SeriesSpec, load_registry
from ipca_nowcast.ingestion.sgs import SgsClient
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_START = dt.date(2003, 1, 1)


@dataclass
class IngestionOutcome:
    series_code: str
    rows_upserted: int
    report: QualityReport


class IngestionService:
    """High-level ingestion that writes series, observations and Focus data."""

    def __init__(
        self,
        session: Session,
        registry_path: Path | str = Path("config/series.yaml"),
        http: HttpClient | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session
        self.cache_dir = cache_dir or settings.raw_data_dir
        self.http = http or HttpClient(cache_dir=self.cache_dir)
        self.registry = load_registry(registry_path)
        self.sgs = SgsClient(http=self.http, cache_dir=self.cache_dir)
        self.focus = FocusClient(http=self.http, cache_dir=self.cache_dir)
        self.series_repo = SeriesRepository(session)
        self.obs_repo = ObservationRepository(session)
        self.focus_repo = FocusRepository(session)
        self.run_repo = IngestionRunRepository(session)

    def sync_registry(self) -> int:
        return self.series_repo.upsert_many([s.as_row() for s in self.registry])

    def ingest_series(
        self,
        spec: SeriesSpec,
        start: dt.date = DEFAULT_START,
        end: dt.date | None = None,
        use_cache: bool = True,
    ) -> IngestionOutcome:
        end = end or dt.date.today()
        if spec.source != "BCB_SGS":
            _logger.info("ingest_skipped_unsupported_source", code=spec.code, source=spec.source)
            return IngestionOutcome(spec.code, 0, check_quality(spec.code, spec.frequency, []))
        series = self.series_repo.get_by_code(spec.code)
        if series is None:
            self.sync_registry()
            series = self.series_repo.get_by_code(spec.code)
            assert series is not None
        points = self.sgs.fetch(spec.external_id, start=start, end=end, use_cache=use_cache)
        rows = self.obs_repo.upsert_many(series.id, points)
        report = check_quality(spec.code, spec.frequency, points)
        _logger.info(
            "ingest_series_done",
            code=spec.code,
            rows=rows,
            n=report.n_points,
            gaps=report.gaps,
            dups=report.duplicates,
        )
        return IngestionOutcome(spec.code, rows, report)

    def ingest_all(
        self,
        start: dt.date = DEFAULT_START,
        end: dt.date | None = None,
        use_cache: bool = True,
    ) -> list[IngestionOutcome]:
        self.sync_registry()
        outcomes: list[IngestionOutcome] = []
        for spec in self.registry:
            outcomes.append(self.ingest_series(spec, start=start, end=end, use_cache=use_cache))
        return outcomes

    def ingest_focus(
        self,
        start_date: dt.date = dt.date(2003, 1, 1),
        use_cache: bool = True,
    ) -> int:
        rows = self.focus.fetch_ipca_monthly(start_date=start_date, use_cache=use_cache)
        return self.focus_repo.upsert_many(rows)

    def seed_from_fixtures(self, fixtures_dir: Path) -> dict[str, int]:
        """Populate the DB from local JSON fixtures (no internet).

        Expects files:
          - `series.yaml` (optional override)
          - `sgs_<code>.json` for each series (payload = SGS list)
          - `focus.json` (payload = Focus OData {value: [...]})
        """
        import json

        self.sync_registry()
        counts: dict[str, int] = {"series": len(self.registry)}
        from ipca_nowcast.ingestion.focus import parse_focus_payload
        from ipca_nowcast.ingestion.sgs import parse_sgs_payload

        total_obs = 0
        for spec in self.registry:
            fixture = fixtures_dir / f"sgs_{spec.external_id}.json"
            if not fixture.exists():
                continue
            series = self.series_repo.get_by_code(spec.code)
            assert series is not None
            payload = json.loads(fixture.read_text(encoding="utf-8"))
            points = parse_sgs_payload(payload)
            total_obs += self.obs_repo.upsert_many(series.id, points)
        counts["observations"] = total_obs

        focus_file = fixtures_dir / "focus.json"
        if focus_file.exists():
            payload = json.loads(focus_file.read_text(encoding="utf-8"))
            rows = parse_focus_payload(payload)
            counts["focus_rows"] = self.focus_repo.upsert_many(rows)
        return counts


__all__ = ["DEFAULT_START", "Decimal", "IngestionOutcome", "IngestionService"]
