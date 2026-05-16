"""Test utils edge cases for coverage."""

from __future__ import annotations

import math

from custom_components.quilt_hp.utils import normalize_temperature


def test_normalize_temperature_none() -> None:
    assert normalize_temperature(None) is None


def test_normalize_temperature_nan() -> None:
    assert normalize_temperature(math.nan) is None


def test_normalize_temperature_valid() -> None:
    assert normalize_temperature(25.5) == 25.5
