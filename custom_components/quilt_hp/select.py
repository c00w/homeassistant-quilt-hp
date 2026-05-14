"""Select platform for Quilt Heat Pump — louver mode and angle per IndoorUnit."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from quilt_hp.models.enums import LouverAngle, LouverMode
from quilt_hp.models.indoor_unit import IndoorUnit

from .coordinator import QuiltCoordinator

if TYPE_CHECKING:
    from . import QuiltConfigEntry
from .entity import QuiltEntity, idu_device_info

_LOUVER_MODE_OPTIONS: list[str] = ["closed", "sweep", "fixed", "auto"]

_STR_TO_LOUVER_MODE: dict[str, LouverMode] = {
    "closed": LouverMode.CLOSED,
    "sweep": LouverMode.SWEEP,
    "fixed": LouverMode.FIXED,
    "auto": LouverMode.AUTO,
}

_LOUVER_MODE_TO_STR: dict[LouverMode, str] = {
    v: k for k, v in _STR_TO_LOUVER_MODE.items()
}

# Option strings are the human-readable labels from LouverAngle.label so the
# HA UI shows them directly without needing a separate translation lookup.
_LOUVER_ANGLE_OPTIONS: list[str] = [a.label for a in LouverAngle]

_LABEL_TO_LOUVER_ANGLE: dict[str, LouverAngle] = {a.label: a for a in LouverAngle}

_LOUVER_ANGLE_TO_LABEL: dict[LouverAngle, str] = {a: a.label for a in LouverAngle}


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QuiltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""
    coordinator = entry.runtime_data
    snapshot = coordinator.data

    entities: list[SelectEntity] = []
    for idu in snapshot.indoor_units:
        entities.append(QuiltLouverModeSelect(coordinator, idu.id))
        entities.append(QuiltLouverAngleSelect(coordinator, idu.id))
    async_add_entities(entities)


class QuiltLouverModeSelect(QuiltEntity, SelectEntity):
    """Select entity for indoor unit louver mode."""

    _attr_options: list[str] = _LOUVER_MODE_OPTIONS
    _attr_translation_key: str = "louver_mode"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        """Initialize the louver mode select entity."""
        super().__init__(coordinator)
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_louver_mode_{idu_id}"
        self._attr_name: str | None = "Louver Mode"

    @property
    def _idu(self) -> IndoorUnit:
        return self.coordinator.idu_by_id[self._idu_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        idu = self._idu
        space = self.coordinator.spaces_by_id.get(idu.space_id)
        return idu_device_info(idu, space)

    @property
    @override
    def available(self) -> bool:
        return super().available and self._idu.is_online

    @property
    @override
    def current_option(self) -> str | None:
        return _LOUVER_MODE_TO_STR.get(self._idu.controls.louver_mode)

    @override
    async def async_select_option(self, option: str) -> None:
        mode = _STR_TO_LOUVER_MODE[option]
        await self.coordinator.async_set_indoor_unit(self._idu, louver_mode=mode)
        await self._async_refresh_if_not_streaming()


class QuiltLouverAngleSelect(QuiltEntity, SelectEntity):
    """Select entity for indoor unit louver angle (relevant when mode=FIXED)."""

    _attr_options: list[str] = _LOUVER_ANGLE_OPTIONS

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        """Initialize the louver angle select entity."""
        super().__init__(coordinator)
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_louver_angle_{idu_id}"
        self._attr_name: str | None = "Louver Angle"

    @property
    def _idu(self) -> IndoorUnit:
        return self.coordinator.idu_by_id[self._idu_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        idu = self._idu
        space = self.coordinator.spaces_by_id.get(idu.space_id)
        return idu_device_info(idu, space)

    @property
    @override
    def available(self) -> bool:
        return super().available and self._idu.is_online

    @property
    @override
    def current_option(self) -> str | None:
        angle = LouverAngle.from_wire(self._idu.controls.louver_fixed_position)
        return _LOUVER_ANGLE_TO_LABEL.get(angle)

    @override
    async def async_select_option(self, option: str) -> None:
        angle = _LABEL_TO_LOUVER_ANGLE[option]
        await self.coordinator.async_set_indoor_unit(
            self._idu,
            louver_mode=LouverMode.FIXED,
            louver_position=angle.to_wire(),
        )
        await self._async_refresh_if_not_streaming()
