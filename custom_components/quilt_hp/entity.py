"""Base entity class for the Quilt Heat Pump integration."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space

from .const import DOMAIN
from .coordinator import QuiltCoordinator

_MANUFACTURER: str = "Quilt"


class QuiltEntity(CoordinatorEntity[QuiltCoordinator]):
    """Common properties for all Quilt entities."""

    _attr_has_entity_name: bool = True

    def __init__(self, coordinator: QuiltCoordinator) -> None:
        """Initialize the Quilt entity."""
        super().__init__(coordinator)


def space_device_info(space: Space) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt space (room/zone)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"s_{space.id}")},
        name=space.name,
        manufacturer=_MANUFACTURER,
        model="Quilt Space",
    )


def idu_device_info(idu: IndoorUnit, _space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an indoor unit."""
    # Link IDU to its space via via_device if the space is known.
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"i_{idu.id}")},
        "name": idu.settings.name or f"Indoor Unit {idu.id[:8]}",
        "manufacturer": _MANUFACTURER,
        "model": "Quilt Indoor Unit",
    }
    if idu.space_id:
        info["via_device"] = (DOMAIN, f"s_{idu.space_id}")

    return cast(DeviceInfo, cast(object, info))


def odu_device_info(odu: OutdoorUnit) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an outdoor unit."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"u_{odu.id}")},
        name=f"Outdoor Unit {odu.id[:8]}",
        manufacturer=_MANUFACTURER,
        model=odu.model_sku or "Quilt Outdoor Unit",
        serial_number=odu.serial_number,
        sw_version=odu.firmware_version,
    )
