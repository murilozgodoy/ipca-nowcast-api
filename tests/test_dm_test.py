"""Tests for the Diebold-Mariano statistic."""

from __future__ import annotations

import math

import pytest

from ipca_nowcast.evaluation.dm_test import diebold_mariano


def test_identical_errors_give_nan_or_zero_stat() -> None:
    e = [0.1, -0.2, 0.3, -0.1, 0.2, -0.3, 0.0, 0.1, -0.1, 0.2, 0.0, 0.1]
    r = diebold_mariano(e, e, h=1)
    # Zero variance → NaN stat
    assert math.isnan(r.dm_stat) or r.dm_stat == 0.0


def test_a_strongly_better_than_b_gives_negative_stat() -> None:
    import random

    random.seed(0)
    a = [random.gauss(0, 0.1) for _ in range(60)]
    b = [random.gauss(0, 1.0) for _ in range(60)]
    r = diebold_mariano(a, b, h=1)
    # Loss(A) < Loss(B), so mean(|a|^2 - |b|^2) < 0 → negative stat, small p
    assert r.dm_stat < 0
    assert r.p_value < 0.05


def test_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        diebold_mariano([1.0, 2.0], [1.0], h=1)
