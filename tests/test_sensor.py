"""Tests for the sensor platform."""

from __future__ import annotations

import math

import pytest

from custom_components.quilt_hp.sensor import (
    IDU_SENSOR_DESCRIPTIONS,
    ODU_SENSOR_DESCRIPTIONS,
    SPACE_SENSOR_DESCRIPTIONS,
    QuiltIDUSensor,
    QuiltODUSensor,
    QuiltSpaceSensor,
)

from .conftest import (
    make_idu,
    make_mock_coordinator,
    make_odu,
    make_snapshot,
    make_space,
)


@pytest.fixture
def coordinator(hass):
    space = make_space(ambient_temp_c=21.5)
    idu = make_idu()
    odu = make_odu()
    snapshot = make_snapshot(spaces=[space], indoor_units=[idu], outdoor_units=[odu])
    return make_mock_coordinator(hass, snapshot)


def test_space_ambient_temperature(coordinator) -> None:
    desc = next(d for d in SPACE_SENSOR_DESCRIPTIONS if d.key == "space_temperature")
    entity = QuiltSpaceSensor(coordinator, "space-001", "idu-001", desc)
    assert entity.native_value == 21.5


def test_space_ambient_temperature_nan_is_none(hass) -> None:
    space = make_space(ambient_temp_c=21.5)
    space.state.ambient_temperature_c = math.nan
    coordinator = make_mock_coordinator(hass, make_snapshot(spaces=[space]))
    desc = next(d for d in SPACE_SENSOR_DESCRIPTIONS if d.key == "space_temperature")
    entity = QuiltSpaceSensor(coordinator, "space-001", "idu-001", desc)
    assert entity.native_value is None


def test_idu_ambient_temperature(coordinator) -> None:
    desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "ambient_temperature")
    entity = QuiltIDUSensor(coordinator, "idu-001", desc)
    assert entity.native_value == 21.5


def test_idu_humidity(coordinator) -> None:
    desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "ambient_humidity")
    entity = QuiltIDUSensor(coordinator, "idu-001", desc)
    assert entity.native_value == 45.0


def test_idu_fan_rpm(coordinator) -> None:
    desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "fan_speed_rpm")
    entity = QuiltIDUSensor(coordinator, "idu-001", desc)
    assert entity.native_value == 800.0


def test_odu_ambient_temperature(coordinator) -> None:
    desc = next(d for d in ODU_SENSOR_DESCRIPTIONS if d.key == "ambient_temperature")
    entity = QuiltODUSensor(coordinator, "odu-001", "idu-001", desc)
    assert entity.native_value == 5.0


def test_odu_compressor_frequency(coordinator) -> None:
    desc = next(d for d in ODU_SENSOR_DESCRIPTIONS if d.key == "compressor_frequency")
    entity = QuiltODUSensor(coordinator, "odu-001", "idu-001", desc)
    assert entity.native_value == 55.0


def test_idu_unavailable_when_offline(hass) -> None:
    idu = make_idu(online=False)
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "ambient_temperature")
    entity = QuiltIDUSensor(coordinator, "idu-001", desc)
    assert not entity.available


def test_idu_inlet_temperature_keeps_zero_value(hass) -> None:
    idu = make_idu()
    idu.state.inlet_temperature_c = 0.0
    coordinator = make_mock_coordinator(hass, make_snapshot(indoor_units=[idu]))
    desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "inlet_temperature")
    entity = QuiltIDUSensor(coordinator, "idu-001", desc)
    assert entity.native_value == 0.0
