"""Tests for the fan platform."""

from __future__ import annotations

import pytest
from quilt_hp.models.enums import FanSpeed

from custom_components.quilt_hp.fan import QuiltFanEntity, _pct_to_fan_speed

from .conftest import make_idu, make_mock_coordinator, make_snapshot


@pytest.fixture
def coordinator(hass):
    idu = make_idu(fan_speed=FanSpeed.MEDIUM)
    snapshot = make_snapshot(indoor_units=[idu])
    return make_mock_coordinator(hass, snapshot)


def test_percentage_medium(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert entity.percentage == 60


def test_percentage_auto(hass) -> None:
    idu = make_idu(fan_speed=FanSpeed.AUTO)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert entity.percentage == 0


def test_pct_to_fan_speed_thresholds() -> None:
    assert _pct_to_fan_speed(0) == FanSpeed.AUTO
    assert _pct_to_fan_speed(20) == FanSpeed.QUIET
    assert _pct_to_fan_speed(40) == FanSpeed.LOW
    assert _pct_to_fan_speed(60) == FanSpeed.MEDIUM
    assert _pct_to_fan_speed(80) == FanSpeed.HIGH
    assert _pct_to_fan_speed(100) == FanSpeed.BLAST


async def test_set_percentage(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_set_percentage(80)
    coordinator.async_set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.HIGH


async def test_turn_off_sets_auto(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_set_preset_mode("auto")
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.AUTO


async def test_set_preset_mode_keeps_requested_value(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_set_preset_mode("medium")
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.MEDIUM


async def test_set_preset_mode(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_set_preset_mode("blast")
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.BLAST


def test_preset_mode(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert entity.preset_mode == "medium"


def test_is_on_false_when_auto(hass) -> None:
    idu = make_idu(fan_speed=FanSpeed.AUTO)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert not entity.is_on


def test_unavailable_when_offline(hass) -> None:
    idu = make_idu(online=False)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert not entity.available
