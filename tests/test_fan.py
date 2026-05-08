"""Tests for the fan platform."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.quilt_hp.fan import QuiltFanEntity, _pct_to_fan_speed
from quilt_hp.models.enums import FanSpeed

from .conftest import make_idu, make_mock_coordinator, make_snapshot


@pytest.fixture
def coordinator(hass):
    idu = make_idu(fan_speed=FanSpeed.MEDIUM)
    snapshot = make_snapshot(indoor_units=[idu])
    return make_mock_coordinator(hass, snapshot)


def test_percentage_medium(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert entity.percentage == 50


def test_percentage_auto(hass) -> None:
    idu = make_idu(fan_speed=FanSpeed.AUTO)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert entity.percentage == 0


def test_pct_to_fan_speed_thresholds() -> None:
    assert _pct_to_fan_speed(0) == FanSpeed.AUTO
    assert _pct_to_fan_speed(17) == FanSpeed.QUIET
    assert _pct_to_fan_speed(33) == FanSpeed.LOW
    assert _pct_to_fan_speed(50) == FanSpeed.MEDIUM
    assert _pct_to_fan_speed(67) == FanSpeed.HIGH
    assert _pct_to_fan_speed(100) == FanSpeed.BLAST


async def test_set_percentage(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_set_percentage(67)
    coordinator.client.set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.client.set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.HIGH


async def test_turn_off_sets_auto(coordinator) -> None:
    entity = QuiltFanEntity(coordinator, "idu-001")
    await entity.async_turn_off()
    call_kwargs = coordinator.client.set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.AUTO


def test_unavailable_when_offline(hass) -> None:
    idu = make_idu(online=False)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltFanEntity(coordinator, "idu-001")
    assert not entity.available
