"""Sensor platform for Quilt Heat Pump.

Provides sensor entities for:
- QSM (IndoorUnit): space temperature (space-calibrated), unit temp, humidity,
                    fan RPM, inlet/outlet temp, presence level,
                    COP, HVAC capacity (W), HVAC power (W)
- OutdoorUnit: ambient temp, compressor frequency, pressures
- Controller (Dial): ambient temperature
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

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
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space
from quilt_hp.models.controller import Controller

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, controller_device_info, idu_device_info, odu_device_info

# ── Space temperature sensor (on QSM device) ──────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SpaceSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Space], Any] = lambda _: None


SPACE_SENSOR_DESCRIPTIONS: tuple[SpaceSensorDescription, ...] = (
    SpaceSensorDescription(
        key="space_temperature",
        name="Space Temperature",
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
            odu.performance_data.compressor_frequency_hz
            if odu.performance_data
            else None
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


# ── Controller (Dial) sensors ─────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class ControllerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Controller], Any] = lambda _: None
    available_fn: Callable[[Controller], bool] = lambda ctrl: ctrl.is_online


CONTROLLER_SENSOR_DESCRIPTIONS: tuple[ControllerSensorDescription, ...] = (
    ControllerSensorDescription(
        key="ambient_temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda ctrl: ctrl.ambient_temperature_c,
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

    # Index the first IDU per space so space-level sensors have a device to live on.
    # A space is always non-functional without at least one IDU, so this is safe.
    first_idu_for_space: dict[str, str] = {}
    for idu in snapshot.indoor_units:
        if idu.space_id and idu.space_id not in first_idu_for_space:
            first_idu_for_space[idu.space_id] = idu.id

    # Space temperature sensors — attached to the first QSM in each space
    for space in snapshot.spaces:
        if not space.is_room:
            continue
        idu_id = first_idu_for_space.get(space.id)
        if idu_id is None:
            continue
        for space_desc in SPACE_SENSOR_DESCRIPTIONS:
            entities.append(QuiltSpaceSensor(coordinator, space.id, idu_id, space_desc))

    # QSM (IndoorUnit) sensors
    for idu in snapshot.indoor_units:
        for idu_desc in IDU_SENSOR_DESCRIPTIONS:
            entities.append(QuiltIDUSensor(coordinator, idu.id, idu_desc))

    # OutdoorUnit sensors
    for odu in snapshot.outdoor_units:
        for odu_desc in ODU_SENSOR_DESCRIPTIONS:
            entities.append(QuiltODUSensor(coordinator, odu.id, odu_desc))

    # Controller (Dial) sensors
    for ctrl in snapshot.controllers:
        for ctrl_desc in CONTROLLER_SENSOR_DESCRIPTIONS:
            entities.append(QuiltControllerSensor(coordinator, ctrl.id, ctrl_desc))

    async_add_entities(entities)


# ── Sensor entity classes ─────────────────────────────────────────────────────


class QuiltSpaceSensor(QuiltEntity, SensorEntity):
    """Space temperature sensor, presented on the first QSM in the space."""

    entity_description: SpaceSensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        space_id: str,
        idu_id: str,
        description: SpaceSensorDescription,
    ) -> None:
        """Initialize the space sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._space_id: str = space_id
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_space_{space_id}_{description.key}"

    @property
    def _space(self) -> Space:
        return self.coordinator.spaces_by_id[self._space_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        idu = self.coordinator.idu_by_id[self._idu_id]
        space = self._space
        return idu_device_info(idu, space)

    @property
    @override
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
        """Initialize the indoor unit sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_{idu_id}_{description.key}"

    @property
    def _idu(self) -> IndoorUnit:
        return self.coordinator.idu_by_id[self._idu_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        idu = self._idu
        space = self.coordinator.spaces_by_id.get(idu.space_id) if idu.space_id else None
        return idu_device_info(idu, space)

    @property
    @override
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self._idu)

    @property
    @override
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
        """Initialize the outdoor unit sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._odu_id: str = odu_id
        self._attr_unique_id: str = f"quilt_odu_{odu_id}_{description.key}"

    @property
    def _odu(self) -> OutdoorUnit:
        return self.coordinator.odu_by_id[self._odu_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        odu = self._odu
        space = self.coordinator.spaces_by_id.get(odu.space_id) if odu.space_id else None
        return odu_device_info(odu, space)

    @property
    @override
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._odu)


class QuiltControllerSensor(QuiltEntity, SensorEntity):
    """Sensor entity for a Quilt Controller (Dial)."""

    entity_description: ControllerSensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        ctrl_id: str,
        description: ControllerSensorDescription,
    ) -> None:
        """Initialize the controller sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._ctrl_id: str = ctrl_id
        self._attr_unique_id: str = f"quilt_ctrl_{ctrl_id}_{description.key}"

    @property
    def _ctrl(self) -> Controller:
        return self.coordinator.ctrl_by_id[self._ctrl_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        ctrl = self._ctrl
        space = self.coordinator.spaces_by_id.get(ctrl.space_id) if ctrl.space_id else None
        return controller_device_info(ctrl, space)

    @property
    @override
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self._ctrl)

    @property
    @override
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._ctrl)
