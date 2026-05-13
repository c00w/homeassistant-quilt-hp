"""Fan platform for Quilt Heat Pump — one entity per IndoorUnit (fan speed)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from quilt_hp.models.enums import FanSpeed
from quilt_hp.models.indoor_unit import IndoorUnit

from .coordinator import QuiltCoordinator

if TYPE_CHECKING:
    from . import QuiltConfigEntry
from .entity import QuiltEntity, idu_device_info

# Map FanSpeed → percentage (for HA's 0-100 speed model).
# AUTO maps to 0 % (no explicit setpoint).
_FAN_TO_PCT: dict[FanSpeed, int] = {
    FanSpeed.AUTO: 0,
    FanSpeed.QUIET: 20,
    FanSpeed.LOW: 40,
    FanSpeed.MEDIUM: 60,
    FanSpeed.HIGH: 80,
    FanSpeed.BLAST: 100,
}

_PCT_THRESHOLDS: list[tuple[int, FanSpeed]] = [
    (10, FanSpeed.AUTO),
    (30, FanSpeed.QUIET),
    (50, FanSpeed.LOW),
    (70, FanSpeed.MEDIUM),
    (90, FanSpeed.HIGH),
    (101, FanSpeed.BLAST),
]

_PRESET_TO_FAN: dict[str, FanSpeed] = {
    "auto": FanSpeed.AUTO,
    "quiet": FanSpeed.QUIET,
    "low": FanSpeed.LOW,
    "medium": FanSpeed.MEDIUM,
    "high": FanSpeed.HIGH,
    "blast": FanSpeed.BLAST,
}

_FAN_TO_PRESET: dict[FanSpeed, str] = {
    speed: preset for preset, speed in _PRESET_TO_FAN.items()
}


def _pct_to_fan_speed(pct: int) -> FanSpeed:
    for threshold, speed in _PCT_THRESHOLDS:
        if pct < threshold:
            return speed
    return FanSpeed.BLAST


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QuiltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up fan entities from a config entry."""
    coordinator = entry.runtime_data
    snapshot = coordinator.data

    entities = [QuiltFanEntity(coordinator, idu.id) for idu in snapshot.indoor_units]
    async_add_entities(entities)


class QuiltFanEntity(QuiltEntity, FanEntity):
    """Fan entity representing an indoor unit's fan speed control."""

    _attr_supported_features: FanEntityFeature = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_translation_key: str = "fan"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_fan_{idu_id}"
        self._attr_name: str | None = "Fan"
        self._attr_preset_modes: list[str] = list(_PRESET_TO_FAN.keys())
        # Cache the last explicit (non-AUTO) speed for restore on turn_on.
        self._last_explicit_speed: FanSpeed = FanSpeed.LOW

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
        return self._idu.controls.fan_speed != FanSpeed.AUTO

    @property
    @override
    def percentage(self) -> int | None:
        return _FAN_TO_PCT.get(self._idu.controls.fan_speed)

    @property
    @override
    def preset_mode(self) -> str | None:
        return _FAN_TO_PRESET.get(self._idu.controls.fan_speed)

    @property
    @override
    def speed_count(self) -> int:
        return len(_FAN_TO_PCT) - 1  # exclude AUTO

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, restoring the last explicit speed if no target is given."""
        if preset_mode is not None:
            fan_speed = _PRESET_TO_FAN[preset_mode]
        elif percentage is not None:
            fan_speed = _pct_to_fan_speed(percentage)
            if fan_speed == FanSpeed.AUTO:
                fan_speed = self._last_explicit_speed
        else:
            fan_speed = self._last_explicit_speed
        self._last_explicit_speed = fan_speed
        await self.coordinator.async_set_indoor_unit(self._idu, fan_speed=fan_speed)
        await self._async_refresh_if_not_streaming()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan by setting it to AUTO (speed determined by HVAC)."""
        await self.coordinator.async_set_indoor_unit(self._idu, fan_speed=FanSpeed.AUTO)
        await self._async_refresh_if_not_streaming()

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        fan_speed = _pct_to_fan_speed(percentage)
        if fan_speed != FanSpeed.AUTO:
            self._last_explicit_speed = fan_speed
        await self.coordinator.async_set_indoor_unit(self._idu, fan_speed=fan_speed)
        await self._async_refresh_if_not_streaming()

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        fan_speed = _PRESET_TO_FAN[preset_mode]
        if fan_speed != FanSpeed.AUTO:
            self._last_explicit_speed = fan_speed
        await self.coordinator.async_set_indoor_unit(self._idu, fan_speed=fan_speed)
        await self._async_refresh_if_not_streaming()
