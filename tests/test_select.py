"""Tests for the select platform (louver mode and angle)."""

from __future__ import annotations

import pytest
from quilt_hp.models.enums import LouverAngle, LouverMode

from custom_components.quilt_hp.select import (
    QuiltLouverAngleSelect,
    QuiltLouverModeSelect,
)

from .conftest import make_idu, make_mock_coordinator, make_snapshot


@pytest.fixture
def coordinator_sweep(hass):
    idu = make_idu(louver_mode=LouverMode.SWEEP)
    snapshot = make_snapshot(indoor_units=[idu])
    return make_mock_coordinator(hass, snapshot)


@pytest.fixture
def coordinator_fixed(hass):
    idu = make_idu(
        louver_mode=LouverMode.FIXED, louver_fixed_position=LouverAngle.ANGLE3.to_wire()
    )
    snapshot = make_snapshot(indoor_units=[idu])
    return make_mock_coordinator(hass, snapshot)


def test_louver_mode_current_option(coordinator_sweep) -> None:
    entity = QuiltLouverModeSelect(coordinator_sweep, "idu-001")
    assert entity.current_option == "sweep"


async def test_louver_mode_select(coordinator_sweep) -> None:
    entity = QuiltLouverModeSelect(coordinator_sweep, "idu-001")
    await entity.async_select_option("auto")
    call_kwargs = coordinator_sweep.async_set_indoor_unit.call_args[1]
    assert call_kwargs["louver_mode"] == LouverMode.AUTO


def test_louver_angle_current_option(coordinator_fixed) -> None:
    entity = QuiltLouverAngleSelect(coordinator_fixed, "idu-001")
    assert entity.current_option == "angle_3"


def test_louver_angle_available_when_not_fixed(coordinator_sweep) -> None:
    entity = QuiltLouverAngleSelect(coordinator_sweep, "idu-001")
    assert entity.available


async def test_louver_angle_select(coordinator_fixed) -> None:
    entity = QuiltLouverAngleSelect(coordinator_fixed, "idu-001")
    await entity.async_select_option("angle_5")
    call_kwargs = coordinator_fixed.async_set_indoor_unit.call_args[1]
    assert call_kwargs["louver_mode"] == LouverMode.FIXED
    assert abs(call_kwargs["louver_position"] - LouverAngle.ANGLE5.to_wire()) < 0.01
