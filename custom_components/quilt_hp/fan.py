"""Fan platform for Quilt Heat Pump — one entity per IndoorUnit (fan speed)."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.enums import FanSpeed

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

    entities = [
        QuiltFanEntity(coordinator, idu.id)
        for idu in snapshot.indoor_units
    ]
    async_add_entities(entities)


class QuiltFanEntity(QuiltEntity, FanEntity):
    """Fan entity representing an indoor unit's fan speed control."""

    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_translation_key = "fan"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        super().__init__(coordinator)
        self._idu_id = idu_id
        self._attr_unique_id = f"quilt_idu_fan_{idu_id}"
        self._attr_name = "Fan"

    @property
    def _idu(self):
        return next(u for u in self.coordinator.data.indoor_units if u.id == self._idu_id)

    @property
    def device_info(self):
        idu = self._idu
        space = next((s for s in self.coordinator.data.spaces if s.id == idu.space_id), None)
        return idu_device_info(idu, space)

    @property
    def available(self) -> bool:
        return super().available and self._idu.is_online

    @property
    def is_on(self) -> bool:
        return self._idu.controls.fan_speed != FanSpeed.AUTO or self._idu.is_online

    @property
    def percentage(self) -> int | None:
        return _FAN_TO_PCT.get(self._idu.controls.fan_speed)

    @property
    def speed_count(self) -> int:
        return len(_FAN_TO_PCT) - 1  # exclude AUTO

    async def async_set_percentage(self, percentage: int) -> None:
        fan_speed = _pct_to_fan_speed(percentage)
        await self.coordinator.client.set_indoor_unit(self._idu, fan_speed=fan_speed)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        speed = _pct_to_fan_speed(percentage) if percentage is not None else FanSpeed.AUTO
        await self.coordinator.client.set_indoor_unit(self._idu, fan_speed=speed)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_indoor_unit(self._idu, fan_speed=FanSpeed.AUTO)
        await self.coordinator.async_request_refresh()
