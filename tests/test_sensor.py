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
    async_setup_entry,
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


def test_odu_unique_id_excludes_idu_id() -> None:
    """ODU unique ID must not include an IDU ID — the ODU is a standalone device."""
    desc = next(d for d in ODU_SENSOR_DESCRIPTIONS if d.key == "ambient_temperature")
    # Simulate two different IDUs both referencing the same ODU
    from unittest.mock import MagicMock

    coordinator = MagicMock()
    entity_a = QuiltODUSensor(coordinator, "odu-001", "idu-001", desc)
    entity_b = QuiltODUSensor(coordinator, "odu-001", "idu-002", desc)
    assert entity_a.unique_id == entity_b.unique_id
    assert "idu" not in (entity_a.unique_id or "")


def test_shared_odu_creates_one_sensor_set(hass) -> None:
    """When two IDUs share an ODU, only one set of ODU sensors should be created."""
    idu1 = make_idu(idu_id="idu-001", space_id="space-001", outdoor_unit_id="odu-001")
    idu2 = make_idu(idu_id="idu-002", space_id="space-002", outdoor_unit_id="odu-001")
    odu = make_odu(odu_id="odu-001")
    snapshot = make_snapshot(indoor_units=[idu1, idu2], outdoor_units=[odu])
    coordinator = make_mock_coordinator(hass, snapshot)

    created: list[QuiltODUSensor] = []

    def capture(entities, **_kwargs):
        created.extend(e for e in entities if isinstance(e, QuiltODUSensor))

    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.entry_id = "test"
    entry.runtime_data = coordinator
    coordinator.hass = hass

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_setup_entry(hass, entry, capture))

    odu_unique_ids = {e.unique_id for e in created}
    assert len(odu_unique_ids) == len(ODU_SENSOR_DESCRIPTIONS), (
        "Expected one sensor per ODU description, got duplicates"
    )
