"""Base entity class for the Quilt Heat Pump integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space

from .const import DOMAIN
from .coordinator import QuiltCoordinator

_MANUFACTURER = "Quilt"


class QuiltEntity(CoordinatorEntity[QuiltCoordinator]):
    """Base class for all Quilt Heat Pump entities.

    Subclasses must set ``_attr_unique_id`` and ``_attr_name``.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: QuiltCoordinator) -> None:
        super().__init__(coordinator)


def space_device_info(space: Space) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt space (room/zone)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"space_{space.id}")},
        name=space.name,
        manufacturer=_MANUFACTURER,
        model="Quilt Space",
    )


def idu_device_info(idu: IndoorUnit, space: Space) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an indoor unit, linked to its space device."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"idu_{idu.id}")},
        name=idu.settings.name or f"Indoor Unit {idu.id[:8]}",
        manufacturer=_MANUFACTURER,
        model="Quilt Indoor Unit",
        via_device=(DOMAIN, f"space_{idu.space_id}"),
    )


def odu_device_info(odu: OutdoorUnit) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an outdoor unit."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"odu_{odu.id}")},
        name=f"Outdoor Unit {odu.id[:8]}",
        manufacturer=_MANUFACTURER,
        model=odu.model_sku or "Quilt Outdoor Unit",
        serial_number=odu.serial_number,
        sw_version=odu.firmware_version,
    )
