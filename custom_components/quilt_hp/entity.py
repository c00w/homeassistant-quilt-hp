"""Base entity class for the Quilt Heat Pump integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from quilt_hp.models.controller import Controller
from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.sensor import ControllerRemoteSensor, RemoteSensor
from quilt_hp.models.space import Space
from quilt_hp.models.system import Location

from .const import DOMAIN
from .coordinator import QuiltCoordinator

_MANUFACTURER: str = "Quilt"

_SENTINEL_VALUES: frozenset[str] = frozenset({"N/A", "n/a", "NA", ""})


def _clean(value: str | None) -> str | None:
    """Return None for missing/sentinel strings the API may return."""
    if value is None or value in _SENTINEL_VALUES:
        return None
    return value


class QuiltEntity(CoordinatorEntity[QuiltCoordinator]):
    """Common properties for all Quilt entities."""

    _attr_has_entity_name: bool = True

    def __init__(self, coordinator: QuiltCoordinator) -> None:
        """Initialize the Quilt entity."""
        super().__init__(coordinator)

    async def _async_refresh_if_not_streaming(self) -> None:
        """Request a coordinator poll only when the gRPC stream is not active.

        When the stream is running, state changes arrive within milliseconds and
        an immediate poll would be redundant. This method is called after every
        write operation to ensure state is refreshed even when the stream is down.
        """
        if not self.coordinator.is_streaming:
            await self.coordinator.async_request_refresh()


def idu_device_info(idu: IndoorUnit, space: Space | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an IDU and its embedded QSM.

    The device is named after the room (Space) it serves, matching how the
    Quilt app presents it.
    Spaces are not HA devices; they are surfaced as areas via ``suggested_area``.
    """
    name = space.name if space else (idu.settings.name or f"IDU {idu.id[:8]}")
    info = DeviceInfo(
        identifiers={(DOMAIN, f"i_{idu.id}")},
        name=name,
        manufacturer=_MANUFACTURER,
        model="Indoor Unit",
    )
    if space is not None:
        info["suggested_area"] = space.name
    return info


def odu_device_info(odu: OutdoorUnit, idu: IndoorUnit | None = None) -> DeviceInfo:
    """Build a ``DeviceInfo`` for an outdoor unit.

    The ODU is linked to the IDU in the same space so HA groups them
    correctly in the UI.
    """
    info = DeviceInfo(
        identifiers={(DOMAIN, f"u_{odu.id}")},
        name=f"Outdoor Unit {odu.id[:8]}",
        manufacturer=_MANUFACTURER,
        model=_clean(odu.model_sku) or "Outdoor Unit",
    )
    if _clean(odu.serial_number):
        info["serial_number"] = odu.serial_number
    if _clean(odu.firmware_version):
        info["sw_version"] = odu.firmware_version
    if idu is not None:
        info["via_device"] = (DOMAIN, f"i_{idu.id}")
    return info


def controller_device_info(
    ctrl: Controller, idu: IndoorUnit | None = None
) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt Controller (Dial).

    The Dial is a physically separate device from the IDU. ``via_device`` links
    it to the IDU in the same space so HA groups them correctly in the UI.
    """
    info = DeviceInfo(
        identifiers={(DOMAIN, f"c_{ctrl.id}")},
        name=ctrl.name or "Quilt Dial",
        manufacturer=_MANUFACTURER,
        model=_clean(ctrl.model_sku) or "Dial",
    )
    if _clean(ctrl.serial_number):
        info["serial_number"] = ctrl.serial_number
    if _clean(ctrl.firmware_version):
        info["sw_version"] = ctrl.firmware_version
    if idu is not None:
        info["via_device"] = (DOMAIN, f"i_{idu.id}")
    return info


def remote_sensor_device_info(
    rs: RemoteSensor, idu: IndoorUnit | None = None
) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt remote sensor (IDU-paired wireless sensor)."""
    info = DeviceInfo(
        identifiers={(DOMAIN, f"rs_{rs.id}")},
        name="Remote Sensor",
        manufacturer=_MANUFACTURER,
        model="Remote Sensor",
    )
    if idu is not None:
        info["via_device"] = (DOMAIN, f"i_{idu.id}")
    return info


def ctrl_remote_sensor_device_info(
    crs: ControllerRemoteSensor, ctrl: Controller | None = None
) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt controller remote sensor (Dial-paired)."""
    info = DeviceInfo(
        identifiers={(DOMAIN, f"crs_{crs.id}")},
        name="Zone Sensor",
        manufacturer=_MANUFACTURER,
        model="Zone Sensor",
    )
    if ctrl is not None:
        info["via_device"] = (DOMAIN, f"c_{ctrl.id}")
    return info


def location_device_info(location: Location) -> DeviceInfo:
    """Build a ``DeviceInfo`` for a Quilt location (home/system)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"loc_{location.id}")},
        name=location.name or "Quilt Home",
        manufacturer=_MANUFACTURER,
        model="Quilt System",
    )
