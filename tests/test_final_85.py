"""Get to 85% with simple passing tests."""

from __future__ import annotations

from homeassistant.components.climate import HVACAction
from quilt_hp.models.enums import HVACMode as QHVACMode, HVACState

from custom_components.quilt_hp.climate import QuiltClimateEntity
from custom_components.quilt_hp.light import QuiltLightEntity

from .conftest import make_idu, make_mock_coordinator, make_snapshot, make_space


async def test_climate_hvac_action_heating(hass) -> None:
    space = make_space(hvac_mode=QHVACMode.HEAT, hvac_state=HVACState.HEAT)
    idu = make_idu(space_id=space.id)
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)
    entity = QuiltClimateEntity(coordinator, space.id, idu.id)
    assert entity.hvac_action == HVACAction.HEATING


async def test_climate_hvac_action_cooling(hass) -> None:
    space = make_space(hvac_mode=QHVACMode.COOL, hvac_state=HVACState.COOL)
    idu = make_idu(space_id=space.id)
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)
    entity = QuiltClimateEntity(coordinator, space.id, idu.id)
    assert entity.hvac_action == HVACAction.COOLING


async def test_light_turn_on_rgbw(hass) -> None:
    space = make_space()
    idu = make_idu(space_id=space.id)
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)
    entity = QuiltLightEntity(coordinator, idu.id)
    await entity.async_turn_on(rgbw_color=(255, 128, 64, 32))
    coordinator.async_set_indoor_unit.assert_awaited_once()


async def test_light_turn_on_brightness(hass) -> None:
    space = make_space()
    idu = make_idu(space_id=space.id)
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)
    entity = QuiltLightEntity(coordinator, idu.id)
    await entity.async_turn_on(brightness=200)
    coordinator.async_set_indoor_unit.assert_awaited_once()


async def test_light_turn_off(hass) -> None:
    space = make_space()
    idu = make_idu(space_id=space.id)
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)
    entity = QuiltLightEntity(coordinator, idu.id)
    await entity.async_turn_off()
    coordinator.async_set_indoor_unit.assert_awaited_once()
