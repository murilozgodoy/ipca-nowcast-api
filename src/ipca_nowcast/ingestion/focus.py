"""Client for the BCB Olinda — Expectativas de Mercado (Focus) OData service."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)

FOCUS_BASE = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativaMercadoMensais"
)


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_month_ref(value: str | None) -> dt.date | None:
    """Focus `DataReferencia` is like 'MM/YYYY'. Normalise to first day of month."""
    if not value:
        return None
    try:
        month, year = value.split("/")
        return dt.date(int(year), int(month), 1)
    except (ValueError, AttributeError):
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


class FocusClient:
    """Pulls monthly IPCA expectations from the OData endpoint."""

    def __init__(
        self,
        http: HttpClient | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.http = http or HttpClient(cache_dir=cache_dir)

    def fetch_ipca_monthly(
        self,
        start_date: dt.date | None = None,
        base_calculo: int = 0,
        top: int = 1000,
        use_cache: bool = False,
    ) -> list[dict[str, Any]]:
        """Olinda rejects URL-encoded `+` for spaces inside `$filter`; we build
        the query string ourselves with `%20` encoding and also cap `$top` at
        1000 (the server returns 400 for larger pages when combined with a
        filter)."""
        filters = ["Indicador eq 'IPCA'", f"baseCalculo eq {base_calculo}"]
        if start_date is not None:
            filters.append(f"Data ge '{start_date.isoformat()}'")
        filter_expr = quote(" and ".join(filters), safe="")
        rows: list[dict[str, Any]] = []
        skip = 0
        while True:
            url = (
                f"{FOCUS_BASE}?$format=json&$filter={filter_expr}"
                f"&$top={top}&$skip={skip}&$orderby=Data"
            )
            payload = self.http.get_json(url, use_cache=use_cache) or {}
            batch: list[dict[str, Any]] = (
                payload.get("value", []) if isinstance(payload, dict) else []
            )
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < top:
                break
            skip += top
            _logger.info("focus_page", skip=skip, got=len(rows))
        return [self._normalise(r) for r in rows]

    @staticmethod
    def _normalise(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "indicator": row.get("Indicador") or "IPCA",
            "reference_date": _parse_month_ref(row.get("DataReferencia")),
            "collected_at": _parse_date(row.get("Data")),
            "base_calculo": int(row.get("baseCalculo") or 0),
            "median": _parse_decimal(row.get("Mediana")),
            "mean": _parse_decimal(row.get("Media")),
            "std_dev": _parse_decimal(row.get("DesvioPadrao")),
            "n_respondents": int(row["numeroRespondentes"])
            if row.get("numeroRespondentes") is not None
            else None,
        }


def parse_focus_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a raw Focus OData payload — exported for tests."""
    rows = payload.get("value", []) if isinstance(payload, dict) else []
    return [FocusClient._normalise(r) for r in rows]
