"""Tests for the quality report (gaps / duplicates / outliers)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from ipca_nowcast.ingestion.quality import check_quality


def test_empty_series() -> None:
    r = check_quality("sgs.433", "monthly", [])
    assert r.n_points == 0
    assert r.gaps == 0


def test_detects_duplicates() -> None:
    pts = [
        (dt.date(2024, 1, 1), Decimal("0.5")),
        (dt.date(2024, 1, 1), Decimal("0.6")),
        (dt.date(2024, 2, 1), Decimal("0.4")),
    ]
    r = check_quality("sgs.433", "monthly", pts)
    assert r.duplicates == 1


def test_detects_monthly_gap() -> None:
    pts = [
        (dt.date(2024, 1, 1), Decimal("0.5")),
        (dt.date(2024, 4, 1), Decimal("0.3")),
    ]
    r = check_quality("sgs.433", "monthly", pts)
    assert r.gaps == 1


def test_outlier_detection_flags_extreme_value() -> None:
    pts = [(dt.date(2024, m, 1), Decimal("0.3")) for m in range(1, 12)]
    pts.append((dt.date(2024, 12, 1), Decimal("50.0")))
    r = check_quality("sgs.433", "monthly", pts)
    assert r.outliers >= 1
