"""Base entity class for the Quilt Heat Pump integration."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space
from quilt_hp.models.controller import Controller

from .const import DOMAIN
from .coordinator import QuiltCoordinator

_MANUFACTURER: str = "Quilt"


class QuiltEntity(CoordinatorEntity[QuiltCoordinator]):
    """Common properties for all Quilt entities."""

    _attr_has_entity_name: bool = True

    def __init__(self, coordinator: QuiltCoordinator) -> None:
        """Initialize the Quilt entity."""
        super().__init__(coordinator)


def idu_device_info(idu: IndoorUnit, space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt Smart Module (QSM / indoor unit).

    Spaces are not physical devices; they map to HA Areas via ``suggested_area``.
    """
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"i_{idu.id}")},
        "name": idu.settings.name or f"QSM {idu.id[:8]}",
        "manufacturer": _MANUFACTURER,
        "model": "Quilt Smart Module",
    }
    if space is not None:
        info["suggested_area"] = space.name

    return cast(DeviceInfo, cast(object, info))


def odu_device_info(odu: OutdoorUnit, space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an outdoor unit."""
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"u_{odu.id}")},
        "name": f"Outdoor Unit {odu.id[:8]}",
        "manufacturer": _MANUFACTURER,
        "model": odu.model_sku or "Quilt Outdoor Unit",
        "serial_number": odu.serial_number,
        "sw_version": odu.firmware_version,
    }
    if space is not None:
        info["suggested_area"] = space.name

    return cast(DeviceInfo, cast(object, info))


def controller_device_info(ctrl: Controller, space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt Controller (Dial)."""
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"c_{ctrl.id}")},
        "name": ctrl.name,
        "manufacturer": _MANUFACTURER,
        "model": ctrl.model_sku or "Quilt Dial",
        "serial_number": ctrl.serial_number,
        "sw_version": ctrl.firmware_version,
    }
    if space is not None:
        info["suggested_area"] = space.name

    return cast(DeviceInfo, cast(object, info))
