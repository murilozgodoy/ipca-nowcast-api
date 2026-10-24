"""Quality checks for ingested series (gaps, duplicates, outliers)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class QualityReport:
    series_code: str
    n_points: int
    first_date: dt.date | None
    last_date: dt.date | None
    duplicates: int
    gaps: int
    outliers: int


def _is_outlier(values: list[Decimal], v: Decimal, k: float = 6.0) -> bool:
    if not values:
        return False
    median = sorted(values)[len(values) // 2]
    deviations = sorted(abs(x - median) for x in values)
    mad = deviations[len(deviations) // 2] or Decimal("0.0000001")
    return abs(v - median) > Decimal(str(k)) * mad


def check_quality(
    code: str,
    frequency: str,
    points: list[tuple[dt.date, Decimal | None]],
) -> QualityReport:
    if not points:
        return QualityReport(code, 0, None, None, 0, 0, 0)
    dates = [p[0] for p in points]
    values = [p[1] for p in points if p[1] is not None]
    duplicates = len(dates) - len(set(dates))
    gaps = 0
    if frequency == "monthly":
        for a, b in pairwise(dates):
            expected = a + relativedelta(months=1)
            if b > expected:
                gaps += 1
    outliers = sum(1 for _, v in points if v is not None and _is_outlier(values, v))
    return QualityReport(
        series_code=code,
        n_points=len(points),
        first_date=dates[0],
        last_date=dates[-1],
        duplicates=duplicates,
        gaps=gaps,
        outliers=outliers,
    )
