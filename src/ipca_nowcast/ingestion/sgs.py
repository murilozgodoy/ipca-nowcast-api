"""Client for the BCB SGS (Sistema Gerenciador de Séries Temporais)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dateutil.relativedelta import relativedelta

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"


def _fmt(d: dt.date) -> str:
    return d.strftime("%d/%m/%Y")


def _parse_sgs_date(value: str) -> dt.date | None:
    """Parse SGS 'DD/MM/YYYY' date string."""
    try:
        return dt.datetime.strptime(value, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _parse_sgs_value(value: str | float | int | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    cleaned = str(value).strip().replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


class SgsClient:
    """Fetch SGS series with automatic window pagination.

    SGS caps per-request windows at ~10 years for daily series; monthly
    series are more lenient but we still slice to keep responses bounded.
    """

    def __init__(
        self,
        http: HttpClient | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.http = http or HttpClient(cache_dir=cache_dir)

    def fetch(
        self,
        code: str,
        start: dt.date,
        end: dt.date,
        window_years: int = 9,
        use_cache: bool = False,
    ) -> list[tuple[dt.date, Decimal | None]]:
        if start > end:
            return []
        points: list[tuple[dt.date, Decimal | None]] = []
        seen: set[dt.date] = set()
        cur = start
        while cur <= end:
            win_end = min(cur + relativedelta(years=window_years) - relativedelta(days=1), end)
            params = {"formato": "json", "dataInicial": _fmt(cur), "dataFinal": _fmt(win_end)}
            url = SGS_URL.format(code=code)
            _logger.info("sgs_fetch", code=code, start=cur, end=win_end)
            payload = self.http.get_json(url, params=params, use_cache=use_cache) or []
            for row in payload:
                d = _parse_sgs_date(row.get("data", ""))
                v = _parse_sgs_value(row.get("valor"))
                if d is None or d in seen:
                    continue
                seen.add(d)
                points.append((d, v))
            cur = win_end + relativedelta(days=1)
        points.sort(key=lambda p: p[0])
        return points


def parse_sgs_payload(payload: list[dict[str, str]]) -> list[tuple[dt.date, Decimal | None]]:
    """Parse a raw SGS payload (list of {data, valor}) — exported for tests."""
    out: list[tuple[dt.date, Decimal | None]] = []
    for row in payload:
        d = _parse_sgs_date(row.get("data", ""))
        v = _parse_sgs_value(row.get("valor"))
        if d is not None:
            out.append((d, v))
    return out
