"""Tests for the climate platform."""

from __future__ import annotations

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.quilt_hp.climate import QuiltClimateEntity
from quilt_hp.models.enums import HVACMode as QHVACMode

from .conftest import make_mock_coordinator, make_snapshot, make_space


@pytest.fixture
def coordinator(hass):
    space = make_space(hvac_mode=QHVACMode.HEAT, ambient_temp_c=21.0, heat_setpoint_c=22.0, cool_setpoint_c=25.0)
    snapshot = make_snapshot(spaces=[space])
    return make_mock_coordinator(hass, snapshot)


def test_hvac_mode_heat(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    assert entity.hvac_mode == HVACMode.HEAT


def test_hvac_mode_off_when_standby(hass) -> None:
    space = make_space(hvac_mode=QHVACMode.STANDBY)
    coordinator = make_mock_coordinator(hass, make_snapshot(spaces=[space]))
    entity = QuiltClimateEntity(coordinator, "space-001")
    assert entity.hvac_mode == HVACMode.OFF


def test_current_temperature(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    assert entity.current_temperature == 21.0


def test_target_temperature_heat_mode(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    assert entity.target_temperature == 22.0


def test_target_temperature_range(hass) -> None:
    space = make_space(hvac_mode=QHVACMode.AUTO, heat_setpoint_c=18.0, cool_setpoint_c=26.0)
    coordinator = make_mock_coordinator(hass, make_snapshot(spaces=[space]))
    entity = QuiltClimateEntity(coordinator, "space-001")
    assert entity.target_temperature_low == 18.0
    assert entity.target_temperature_high == 26.0


async def test_set_hvac_mode(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    await entity.async_set_hvac_mode(HVACMode.COOL)
    coordinator.client.set_space.assert_awaited_once()
    call_kwargs = coordinator.client.set_space.call_args[1]
    assert call_kwargs["mode"] == QHVACMode.COOL


async def test_set_temperature_single(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    await entity.async_set_temperature(temperature=23.0)
    coordinator.client.set_space.assert_awaited_once()
    call_kwargs = coordinator.client.set_space.call_args[1]
    assert call_kwargs["cool_setpoint_c"] == 23.0


async def test_set_temperature_range(coordinator) -> None:
    entity = QuiltClimateEntity(coordinator, "space-001")
    await entity.async_set_temperature(target_temp_low=19.0, target_temp_high=27.0)
    coordinator.client.set_space.assert_awaited_once()
    call_kwargs = coordinator.client.set_space.call_args[1]
    assert call_kwargs["heat_setpoint_c"] == 19.0
    assert call_kwargs["cool_setpoint_c"] == 27.0
