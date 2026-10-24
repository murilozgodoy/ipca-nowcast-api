"""Point-forecast metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence


def rmse(errors: Sequence[float]) -> float:
    arr = [e for e in errors if not math.isnan(e)]
    if not arr:
        return float("nan")
    return math.sqrt(sum(e * e for e in arr) / len(arr))


def mae(errors: Sequence[float]) -> float:
    arr = [e for e in errors if not math.isnan(e)]
    if not arr:
        return float("nan")
    return sum(abs(e) for e in arr) / len(arr)


def bias(errors: Sequence[float]) -> float:
    arr = [e for e in errors if not math.isnan(e)]
    if not arr:
        return float("nan")
    return sum(arr) / len(arr)
