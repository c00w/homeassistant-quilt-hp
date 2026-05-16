"""Additional simple tests to boost coverage."""

from __future__ import annotations

from quilt_hp.models.enums import FanSpeed, LouverMode

from custom_components.quilt_hp.fan import QuiltFanEntity
from custom_components.quilt_hp.light import QuiltLightEntity
from custom_components.quilt_hp.select import (
    QuiltLouverAngleSelect,
    QuiltLouverModeSelect,
)
from custom_components.quilt_hp.sensor import QuiltSpaceSensor
from custom_components.quilt_hp.switch import QuiltScheduleSwitch

from .conftest import (
    make_idu,
    make_location,
    make_mock_coordinator,
    make_snapshot,
    make_space,
)


async def test_fan_turn_off(hass) -> None:
    """Test turning fan off sets AUTO."""
    idu = make_idu(fan_speed=FanSpeed.MEDIUM)

    snapshot = make_snapshot(indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltFanEntity(coordinator, idu.id)

    await entity.async_turn_off()

    coordinator.async_set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["fan_speed"] == FanSpeed.AUTO


async def test_light_turn_on_with_brightness(hass) -> None:
    """Test turning on light with brightness."""
    idu = make_idu(led_on=False)

    snapshot = make_snapshot(indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltLightEntity(coordinator, idu.id)

    await entity.async_turn_on(brightness=200)

    coordinator.async_set_indoor_unit.assert_awaited_once()


async def test_light_turn_on_with_rgbw(hass) -> None:
    """Test turning on light with RGBW color."""
    idu = make_idu(led_on=False)

    snapshot = make_snapshot(indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltLightEntity(coordinator, idu.id)

    await entity.async_turn_on(rgbw_color=(255, 0, 0, 0))

    coordinator.async_set_indoor_unit.assert_awaited_once()


async def test_select_louver_mode_closed(hass) -> None:
    """Test setting louver mode to closed."""
    idu = make_idu(louver_mode=LouverMode.AUTO)

    snapshot = make_snapshot(indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltLouverModeSelect(coordinator, idu.id)

    await entity.async_select_option("closed")

    coordinator.async_set_indoor_unit.assert_awaited_once()
    call_kwargs = coordinator.async_set_indoor_unit.call_args[1]
    assert call_kwargs["louver_mode"] == LouverMode.CLOSED


async def test_select_louver_angle_availability(hass) -> None:
    """Test louver angle select availability."""
    idu = make_idu(louver_mode=LouverMode.FIXED)

    snapshot = make_snapshot(indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltLouverAngleSelect(coordinator, idu.id)

    assert entity.available


async def test_sensor_space_temperature(hass) -> None:
    """Test space temperature sensor."""
    from custom_components.quilt_hp.sensor import SPACE_SENSOR_DESCRIPTIONS

    space = make_space(ambient_temp_c=21.5)
    idu = make_idu(space_id=space.id)

    snapshot = make_snapshot(spaces=[space], indoor_units=[idu])
    coordinator = make_mock_coordinator(hass, snapshot)

    # Temperature is the first sensor
    entity = QuiltSpaceSensor(
        coordinator, space.id, idu.id, SPACE_SENSOR_DESCRIPTIONS[0]
    )

    assert entity.native_value == 21.5


async def test_switch_is_on(hass) -> None:
    """Test schedule switch is_on property."""
    location = make_location(schedule_paused=False)

    snapshot = make_snapshot(locations=[location])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltScheduleSwitch(coordinator, location.id)

    # When not paused, switch is on
    assert entity.is_on is True


async def test_switch_is_off(hass) -> None:
    """Test schedule switch is_off when paused."""
    location = make_location(schedule_paused=True)

    snapshot = make_snapshot(locations=[location])
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltScheduleSwitch(coordinator, location.id)

    # When paused, switch is off
    assert entity.is_on is False
