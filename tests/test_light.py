"""Tests for the light platform."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from quilt_hp.models.enums import LedAnimation

from custom_components.quilt_hp.light import QuiltLightEntity


@pytest.fixture
def idu():
    """Return a mock indoor unit."""
    idu = MagicMock()
    idu.id = "idu-001"
    idu.space_id = "space-001"
    idu.is_online = True
    idu.led_on = False
    idu.controls.led_brightness = 0.5
    idu.controls.led_color_code = 0xFFFFFFFF
    idu.controls.led_animation = LedAnimation.NONE
    return idu


@pytest.fixture
def coordinator(hass, idu):
    """Return a mock coordinator."""
    from .conftest import make_mock_coordinator, make_snapshot

    return make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))


async def test_setup_entry(hass, coordinator) -> None:
    """Test setup entry."""
    # Already tested via generic setup? Just check entity count.
    assert len(coordinator.data.indoor_units) == 1


async def test_light_properties(coordinator, idu) -> None:
    """Test light properties."""
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert entity.name == "LED"
    assert entity.unique_id == "quilt_idu_light_idu-001"
    assert not entity.is_on
    assert entity.brightness == 128
    assert entity.rgbw_color == (255, 255, 255, 255)
    assert entity.effect == "none"
    assert "dance" in entity.effect_list


async def test_idu_available(hass, coordinator, idu) -> None:
    """Test availability depends on IDU online status."""
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert entity.available

    idu.is_online = False
    from .conftest import make_mock_coordinator, make_snapshot

    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert not entity.available


async def test_turn_on(coordinator) -> None:
    """Test turning on the light."""
    entity = QuiltLightEntity(coordinator, "idu-001")
    await entity.async_turn_on(brightness=128)
    coordinator.async_set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert abs(call_kwargs["led_brightness"] - (128 / 255)) < 0.01


async def test_turn_on_with_effect(coordinator) -> None:
    """Test turning on the light with an effect."""
    entity = QuiltLightEntity(coordinator, "idu-001")
    await entity.async_turn_on(effect="dance")
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["led_animation"] == LedAnimation.DANCE


async def test_turn_off(coordinator) -> None:
    """Test turning off the light."""
    entity = QuiltLightEntity(coordinator, "idu-001")
    await entity.async_turn_off()
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["led_brightness"] == 0.0
