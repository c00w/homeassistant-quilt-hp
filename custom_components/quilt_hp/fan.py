"""Fan platform for Quilt Heat Pump — one entity per IndoorUnit (fan speed)."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.enums import FanSpeed
from quilt_hp.models.indoor_unit import IndoorUnit

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, idu_device_info

# Map FanSpeed → percentage (for HA's 0-100 speed model).
# AUTO maps to 0 % (no explicit setpoint).
_FAN_TO_PCT: dict[FanSpeed, int] = {
    FanSpeed.AUTO: 0,
    FanSpeed.QUIET: 17,
    FanSpeed.LOW: 33,
    FanSpeed.MEDIUM: 50,
    FanSpeed.HIGH: 67,
    FanSpeed.BLAST: 100,
}

_PCT_THRESHOLDS: list[tuple[int, FanSpeed]] = [
    (8, FanSpeed.AUTO),
    (25, FanSpeed.QUIET),
    (42, FanSpeed.LOW),
    (58, FanSpeed.MEDIUM),
    (83, FanSpeed.HIGH),
    (101, FanSpeed.BLAST),
]


def _pct_to_fan_speed(pct: int) -> FanSpeed:
    for threshold, speed in _PCT_THRESHOLDS:
        if pct < threshold:
            return speed
    return FanSpeed.BLAST


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan entities from a config entry."""
    coordinator: QuiltCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data

    entities = [QuiltFanEntity(coordinator, idu.id) for idu in snapshot.indoor_units]
    async_add_entities(entities)


class QuiltFanEntity(QuiltEntity, FanEntity):
    """Fan entity representing an indoor unit's fan speed control."""

    _attr_supported_features: FanEntityFeature = FanEntityFeature.SET_SPEED
    _attr_translation_key: str = "fan"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_fan_{idu_id}"
        self._attr_name: str | None = "Fan"

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
    def is_on(self) -> bool:
        return self._idu.controls.fan_speed != FanSpeed.AUTO or self._idu.is_online

    @property
    @override
    def percentage(self) -> int | None:
        return _FAN_TO_PCT.get(self._idu.controls.fan_speed)

    @property
    @override
    def speed_count(self) -> int:
        return len(_FAN_TO_PCT) - 1  # exclude AUTO

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        fan_speed = _pct_to_fan_speed(percentage)
        await self.coordinator.client.set_indoor_unit(self._idu, fan_speed=fan_speed)
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        speed = (
            _pct_to_fan_speed(percentage) if percentage is not None else FanSpeed.AUTO
        )
        await self.coordinator.client.set_indoor_unit(self._idu, fan_speed=speed)
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_indoor_unit(
            self._idu, fan_speed=FanSpeed.AUTO
        )
        await self.coordinator.async_request_refresh()
