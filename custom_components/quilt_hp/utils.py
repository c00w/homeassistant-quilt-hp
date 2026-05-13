"""Shared utilities for the Quilt Heat Pump integration."""

from __future__ import annotations

import math


def normalize_temperature(value: float | None) -> float | None:
    """Return *value* unchanged, or ``None`` if it is ``None`` or ``NaN``.

    The Quilt API uses ``NaN`` as a sentinel for "no reading available".
    Home Assistant expects ``None`` for unknown numeric sensor values.
    """
    if value is None or math.isnan(value):
        return None
    return value
