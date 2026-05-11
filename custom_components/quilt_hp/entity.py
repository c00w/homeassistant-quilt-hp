"""Base entity class for the Quilt Heat Pump integration."""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from quilt_hp.models.controller import Controller
from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space

from .const import DOMAIN
from .coordinator import QuiltCoordinator

_LOGGER = logging.getLogger(__name__)
_MANUFACTURER: str = "Quilt"


class QuiltEntity(CoordinatorEntity[QuiltCoordinator]):
    """Common properties for all Quilt entities."""

    _attr_has_entity_name: bool = True

    def __init__(self, coordinator: QuiltCoordinator) -> None:
        """Initialize the Quilt entity."""
        super().__init__(coordinator)


def idu_device_info(idu: IndoorUnit, space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an IDU and its embedded QSM.

    The device is named after the room (Space) it serves, matching how the
    Quilt app presents it. The model is the IDU's configured name.
    Spaces are not HA devices; they are surfaced as areas via ``suggested_area``.
    """
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"i_{idu.id}")},
        "name": space.name if space else (idu.settings.name or f"IDU {idu.id[:8]}"),
        "manufacturer": _MANUFACTURER,
        "model": idu.settings.name or "Quilt Smart Module",
    }
    if space is not None:
        info["suggested_area"] = space.name

    return cast(DeviceInfo, cast(object, info))


def odu_device_info(odu: OutdoorUnit) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an outdoor unit."""
    _LOGGER.debug(
        "ODU device info: id=%s, model_sku=%r, serial=%r, fw=%r",
        odu.id,
        odu.model_sku,
        odu.serial_number,
        odu.firmware_version,
    )
    return DeviceInfo(
        identifiers={(DOMAIN, f"u_{odu.id}")},
        name=f"Outdoor Unit {odu.id[:8]}",
        manufacturer=_MANUFACTURER,
        model=odu.model_sku or "Quilt Outdoor Unit",
        serial_number=odu.serial_number,
        sw_version=odu.firmware_version,
    )


def controller_device_info(ctrl: Controller, idu: IndoorUnit | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt Controller (Dial).

    The Dial is a physically separate device from the IDU. ``via_device`` links
    it to the IDU in the same space so HA groups them correctly in the UI.
    """
    _LOGGER.debug(
        "Controller device info: id=%s, name=%s, model_sku=%r, serial=%r, fw=%r",
        ctrl.id,
        ctrl.name,
        ctrl.model_sku,
        ctrl.serial_number,
        ctrl.firmware_version,
    )
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, f"c_{ctrl.id}")},
        "name": ctrl.name or "Quilt Dial",
        "manufacturer": _MANUFACTURER,
        "model": ctrl.model_sku or "Quilt Dial",
        "serial_number": ctrl.serial_number,
        "sw_version": ctrl.firmware_version,
    }
    if idu is not None:
        info["via_device"] = (DOMAIN, f"i_{idu.id}")

    return cast(DeviceInfo, cast(object, info))
