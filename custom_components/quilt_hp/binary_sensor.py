"""Binary sensor platform for Quilt Heat Pump.

Provides binary sensor entities for:
- QSM/IDU: motion (phase radar), presence (target radar), occupied, online
- Controller (Dial): online
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.controller import Controller
from quilt_hp.models.enums import OccupancyState, Presence
from quilt_hp.models.indoor_unit import IndoorUnit

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, controller_device_info, idu_device_info

# ── IDU binary sensors ────────────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class IDUBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[IndoorUnit], bool | None] = lambda _: None
    available_fn: Callable[[IndoorUnit], bool] = lambda idu: idu.is_online


IDU_BINARY_SENSOR_DESCRIPTIONS: tuple[IDUBinarySensorDescription, ...] = (
    IDUBinarySensorDescription(
        key="motion",
        name="Motion",
        device_class=BinarySensorDeviceClass.MOTION,
        value_fn=lambda idu: (
            idu.presence.sensor0_presence == Presence.DETECTED
            if idu.presence is not None
            else None
        ),
    ),
    IDUBinarySensorDescription(
        key="presence",
        name="Presence",
        device_class=BinarySensorDeviceClass.PRESENCE,
        value_fn=lambda idu: (
            idu.presence.sensor1_presence == Presence.DETECTED
            if idu.presence is not None
            else None
        ),
    ),
    IDUBinarySensorDescription(
        key="occupied",
        name="Occupied",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda idu: (
            None
            if (s := idu.effective_occupancy_state) is None
            else s == OccupancyState.DETECTED
        ),
    ),
    IDUBinarySensorDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda idu: idu.is_online,
        available_fn=lambda _: True,
        entity_registry_enabled_default=False,
    ),
)


# ── Controller binary sensors ─────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class ControllerBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Controller], bool | None] = lambda _: None
    available_fn: Callable[[Controller], bool] = lambda _: True


CONTROLLER_BINARY_SENSOR_DESCRIPTIONS: tuple[ControllerBinarySensorDescription, ...] = (
    ControllerBinarySensorDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda ctrl: ctrl.is_online,
        entity_registry_enabled_default=False,
    ),
)


# ── Platform setup ────────────────────────────────────────────────────────────


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator: QuiltCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data
    entities: list[BinarySensorEntity] = []

    for idu in snapshot.indoor_units:
        for desc in IDU_BINARY_SENSOR_DESCRIPTIONS:
            entities.append(QuiltIDUBinarySensor(coordinator, idu.id, desc))

    for ctrl in snapshot.controllers:
        for ctrl_desc in CONTROLLER_BINARY_SENSOR_DESCRIPTIONS:
            entities.append(
                QuiltControllerBinarySensor(coordinator, ctrl.id, ctrl_desc)
            )

    async_add_entities(entities)


# ── Binary sensor entity classes ──────────────────────────────────────────────


class QuiltIDUBinarySensor(QuiltEntity, BinarySensorEntity):
    """Binary sensor entity for a Quilt indoor unit (QSM)."""

    entity_description: IDUBinarySensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        idu_id: str,
        description: IDUBinarySensorDescription,
    ) -> None:
        """Initialize the IDU binary sensor entity."""
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
        space = (
            self.coordinator.spaces_by_id.get(idu.space_id) if idu.space_id else None
        )
        return idu_device_info(idu, space)

    @property
    @override
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self._idu)

    @property
    @override
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self._idu)


class QuiltControllerBinarySensor(QuiltEntity, BinarySensorEntity):
    """Binary sensor entity for a Quilt Controller (Dial)."""

    entity_description: ControllerBinarySensorDescription

    def __init__(
        self,
        coordinator: QuiltCoordinator,
        ctrl_id: str,
        description: ControllerBinarySensorDescription,
    ) -> None:
        """Initialize the controller binary sensor entity."""
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
        idu = (
            self.coordinator.idu_by_space_id.get(ctrl.space_id)
            if ctrl.space_id
            else None
        )
        return controller_device_info(ctrl, idu)

    @property
    @override
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self._ctrl)

    @property
    @override
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self._ctrl)
