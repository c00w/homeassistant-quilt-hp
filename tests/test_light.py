"""Tests for the light platform."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.quilt_hp.light import QuiltLightEntity, _decode_rgbw, _encode_rgbw
from quilt_hp.models.enums import LightState

from .conftest import make_idu, make_mock_coordinator, make_snapshot


@pytest.fixture
def coordinator(hass):
    idu = make_idu(led_on=True, led_brightness=0.8, led_color_code=0xFF460064)
    snapshot = make_snapshot(indoor_units=[idu])
    return make_mock_coordinator(hass, snapshot)


def test_is_on(coordinator) -> None:
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert entity.is_on is True


def test_is_off(hass) -> None:
    idu = make_idu(led_on=False)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert entity.is_on is False


def test_brightness(coordinator) -> None:
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert entity.brightness == round(0.8 * 255)


def test_rgbw_decode_encode_roundtrip() -> None:
    original = (255, 70, 0, 100)
    code = _encode_rgbw(*original)
    decoded = _decode_rgbw(code)
    assert decoded == original


def test_unavailable_when_offline(hass) -> None:
    idu = make_idu(online=False)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    entity = QuiltLightEntity(coordinator, "idu-001")
    assert not entity.available


async def test_turn_on(coordinator) -> None:
    entity = QuiltLightEntity(coordinator, "idu-001")
    await entity.async_turn_on(brightness=128)
    coordinator.client.set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.client.set_indoor_unit.call_args[1]
    assert call_kwargs["led_state"] == LightState.ON
    assert abs(call_kwargs["led_brightness"] - (128 / 255)) < 0.01


async def test_turn_off(coordinator) -> None:
    entity = QuiltLightEntity(coordinator, "idu-001")
    await entity.async_turn_off()
    call_kwargs = coordinator.client.set_indoor_unit.call_args[1]
    assert call_kwargs["led_state"] == LightState.OFF
