"""Minimal ANP client — weekly fuel-price survey aggregated to monthly means.

The ANP (Agência Nacional do Petróleo) publishes a weekly ``Levantamento de
Preços e Margens de Comercialização dos Combustíveis`` as semicolon-separated
CSV. We fetch the CSV, filter by product (default: gasolina comum) and
reduce to a national monthly mean.

The default URL points at ANP's open-data portal; for tests we pass a
local ``file://`` path to a fixture CSV.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)

ANP_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "arquivos/precos/semanal_combustiveis.csv"
)


def _month_start(d: dt.date) -> dt.date:
    return dt.date(d.year, d.month, 1)


def _parse_br_date(value: str) -> dt.date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_br_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


class AnpClient:
    """Downloads an ANP CSV and reduces it to monthly mean prices by product."""

    def __init__(self, http: HttpClient | None = None, cache_dir: Path | None = None) -> None:
        _ = http  # retained for API symmetry
        _ = cache_dir
        self._timeout = 60.0

    def fetch_monthly(
        self,
        product: str = "GASOLINA COMUM",
        url: str | None = None,
    ) -> list[tuple[dt.date, Decimal | None]]:
        """Return a list of ``(month_start, mean_price_BRL_per_litre)``."""
        source = url or ANP_URL
        if source.startswith("file://"):
            text = Path(source[len("file://") :]).read_text(encoding="utf-8")
        else:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(source)
                response.raise_for_status()
                text = response.content.decode("latin-1", errors="replace")
        return parse_anp_csv(text, product=product)


def parse_anp_csv(
    text: str, product: str = "GASOLINA COMUM"
) -> list[tuple[dt.date, Decimal | None]]:
    """Reduce an ANP weekly CSV to a monthly mean series for one product."""
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    buckets: dict[dt.date, list[Decimal]] = {}
    for row in reader:
        prod = (row.get("PRODUTO") or row.get("Produto") or "").strip().upper()
        if product.upper() not in prod:
            continue
        raw_date = (
            row.get("DATA INICIAL")
            or row.get("Data Inicial")
            or row.get("DATA FINAL")
            or row.get("Data Final")
            or ""
        )
        d = _parse_br_date(raw_date)
        if d is None:
            continue
        value = (
            row.get("PREÇO MÉDIO REVENDA")
            or row.get("Preço Médio Revenda")
            or row.get("PRECO MEDIO REVENDA")
            or ""
        )
        v = _parse_br_decimal(value)
        if v is None:
            continue
        buckets.setdefault(_month_start(d), []).append(v)
    out: list[tuple[dt.date, Decimal | None]] = []
    for month in sorted(buckets):
        values = buckets[month]
        mean: Decimal | None = Decimal(sum(values)) / Decimal(len(values)) if values else None
        out.append((month, mean))
    _logger.info("anp_parsed", months=len(out), product=product)
    return out
