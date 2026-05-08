"""Sensor platform for Quilt Heat Pump.

Provides sensor entities for:
- Space: ambient temperature
- IndoorUnit: temp, humidity, fan RPM, inlet/outlet temp, presence level,
              COP, HVAC capacity (W), HVAC power (W)
- OutdoorUnit: ambient temp, compressor frequency, pressures
- Energy: per-space hourly kWh (polled separately)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, idu_device_info, odu_device_info, space_device_info


# ── Space sensors ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class SpaceSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Space], Any] = lambda _: None


SPACE_SENSOR_DESCRIPTIONS: tuple[SpaceSensorDescription, ...] = (
    SpaceSensorDescription(
        key="ambient_temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda space: space.state.ambient_temperature_c,
    ),
)


# ── IndoorUnit sensors ────────────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class IDUSensorDescription(SensorEntityDescription):
    value_fn: Callable[[IndoorUnit], Any] = lambda _: None
    available_fn: Callable[[IndoorUnit], bool] = lambda idu: idu.is_online


IDU_SENSOR_DESCRIPTIONS: tuple[IDUSensorDescription, ...] = (
    IDUSensorDescription(
        key="ambient_temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda idu: idu.state.ambient_temperature_c,
    ),
    IDUSensorDescription(
        key="ambient_humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda idu: idu.state.ambient_humidity_percent,
    ),
    IDUSensorDescription(
        key="fan_speed_rpm",
        name="Fan Speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda idu: idu.state.fan_speed_rpm,
    ),
    IDUSensorDescription(
        key="inlet_temperature",
        name="Inlet Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda idu: idu.state.inlet_temperature_c or None,
        entity_registry_enabled_default=False,
    ),
    IDUSensorDescription(
        key="outlet_temperature",
        name="Outlet Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda idu: idu.state.outlet_temperature_c or None,
        entity_registry_enabled_default=False,
    ),
    IDUSensorDescription(
        key="presence_level",
        name="Presence Level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda idu: round(idu.state.presence_detection_level * 100, 1),
        entity_registry_enabled_default=False,
    ),
    IDUSensorDescription(
        key="hvac_capacity",
        name="HVAC Capacity",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda idu: (
            idu.performance_metrics.capacity_w if idu.performance_metrics else None
        ),
        entity_registry_enabled_default=False,
    ),
    IDUSensorDescription(
        key="hvac_power",
        name="HVAC Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda idu: (
            idu.performance_metrics.hvac_power_w if idu.performance_metrics else None
        ),
        entity_registry_enabled_default=False,
    ),
    IDUSensorDescription(
        key="coefficient_of_performance",
        name="COP",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda idu: (
            round(idu.performance_metrics.coefficient_of_performance, 2)
            if idu.performance_metrics
            else None
        ),
        entity_registry_enabled_default=False,
    ),
)


# ── OutdoorUnit sensors ───────────────────────────────────────────────────────

@dataclass(frozen=True, kw_only=True)
class ODUSensorDescription(SensorEntityDescription):
    value_fn: Callable[[OutdoorUnit], Any] = lambda _: None


ODU_SENSOR_DESCRIPTIONS: tuple[ODUSensorDescription, ...] = (
    ODUSensorDescription(
        key="ambient_temperature",
        name="Outdoor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda odu: (
            odu.performance_data.ambient_temperature_c if odu.performance_data else None
        ),
    ),
    ODUSensorDescription(
        key="compressor_frequency",
        name="Compressor Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda odu: (
            odu.performance_data.compressor_frequency_hz if odu.performance_data else None
        ),
        entity_registry_enabled_default=False,
    ),
    ODUSensorDescription(
        key="high_pressure",
        name="High-Side Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=lambda odu: (
            odu.performance_data.high_pressure_kpa if odu.performance_data else None
        ),
        entity_registry_enabled_default=False,
    ),
    ODUSensorDescription(
        key="low_pressure",
        name="Low-Side Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=lambda odu: (
            odu.performance_data.low_pressure_kpa if odu.performance_data else None
        ),
        entity_registry_enabled_default=False,
    ),
)


# ── Platform setup ────────────────────────────────────────────────────────────

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: QuiltCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data
    entities: list[SensorEntity] = []

    # Space sensors
    for space in snapshot.spaces:
        if not space.is_room:
            continue
        for desc in SPACE_SENSOR_DESCRIPTIONS:
            entities.append(QuiltSpaceSensor(coordinator, space.id, desc))

    # IndoorUnit sensors
    for idu in snapshot.indoor_units:
        for desc in IDU_SENSOR_DESCRIPTIONS:
            entities.append(QuiltIDUSensor(coordinator, idu.id, desc))

    # OutdoorUnit sensors
    for odu in snapshot.outdoor_units:
        for desc in ODU_SENSOR_DESCRIPTIONS:
            entities.append(QuiltODUSensor(coordinator, odu.id, desc))

    async_add_entities(entities)


# ── Sensor entity classes ─────────────────────────────────────────────────────

class QuiltSpaceSensor(QuiltEntity, SensorEntity):
    """Sensor entity for a Quilt space."""

    entity_description: SpaceSensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        space_id: str,
        description: SpaceSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._space_id = space_id
        self._attr_unique_id = f"quilt_space_{space_id}_{description.key}"

    @property
    def _space(self) -> Space:
        return next(s for s in self.coordinator.data.spaces if s.id == self._space_id)

    @property
    def device_info(self):
        return space_device_info(self._space)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._space)


class QuiltIDUSensor(QuiltEntity, SensorEntity):
    """Sensor entity for a Quilt indoor unit."""

    entity_description: IDUSensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        idu_id: str,
        description: IDUSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._idu_id = idu_id
        self._attr_unique_id = f"quilt_idu_{idu_id}_{description.key}"

    @property
    def _idu(self) -> IndoorUnit:
        return next(u for u in self.coordinator.data.indoor_units if u.id == self._idu_id)

    @property
    def device_info(self):
        idu = self._idu
        space = next((s for s in self.coordinator.data.spaces if s.id == idu.space_id), None)
        return idu_device_info(idu, space)

    @property
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self._idu)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._idu)


class QuiltODUSensor(QuiltEntity, SensorEntity):
    """Sensor entity for a Quilt outdoor unit."""

    entity_description: ODUSensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        odu_id: str,
        description: ODUSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._odu_id = odu_id
        self._attr_unique_id = f"quilt_odu_{odu_id}_{description.key}"

    @property
    def _odu(self) -> OutdoorUnit:
        return next(u for u in self.coordinator.data.outdoor_units if u.id == self._odu_id)

    @property
    def device_info(self):
        return odu_device_info(self._odu)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._odu)
