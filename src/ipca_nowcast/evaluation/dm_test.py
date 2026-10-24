"""Diebold-Mariano test for equal predictive accuracy.

Reference: Diebold & Mariano (1995); Harvey, Leybourne & Newbold (1997)
small-sample correction. Null hypothesis: both forecasts have equal
expected loss.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from scipy.stats import norm


@dataclass(frozen=True)
class DMResult:
    dm_stat: float
    p_value: float
    n: int


def diebold_mariano(
    errors_a: Sequence[float],
    errors_b: Sequence[float],
    h: int = 1,
    power: int = 2,
) -> DMResult:
    """Two-sided DM test. ``h`` is the forecast horizon used for HAC lag."""
    if len(errors_a) != len(errors_b):
        raise ValueError("errors_a and errors_b must have the same length")
    paired = [
        (abs(a) ** power - abs(b) ** power)
        for a, b in zip(errors_a, errors_b, strict=True)
        if not (math.isnan(a) or math.isnan(b))
    ]
    n = len(paired)
    if n < max(10, 2 * h):
        return DMResult(dm_stat=float("nan"), p_value=float("nan"), n=n)
    mean_d = sum(paired) / n
    centered = [d - mean_d for d in paired]
    gamma0 = sum(c * c for c in centered) / n
    gamma_h = 0.0
    for k in range(1, h):
        g = sum(centered[t] * centered[t - k] for t in range(k, n)) / n
        gamma_h += 2.0 * g
    variance = (gamma0 + gamma_h) / n
    if variance <= 0:
        return DMResult(dm_stat=float("nan"), p_value=float("nan"), n=n)
    dm = mean_d / math.sqrt(variance)
    # Harvey small-sample correction
    correction = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_hat = dm * correction
    p_value = 2.0 * (1.0 - norm.cdf(abs(dm_hat)))
    return DMResult(dm_stat=float(dm_hat), p_value=float(p_value), n=n)
