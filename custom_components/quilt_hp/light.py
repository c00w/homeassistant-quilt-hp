"""Light platform for Quilt Heat Pump — one entity per IndoorUnit (LED)."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.indoor_unit import IndoorUnit

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, idu_device_info


def _encode_rgbw(r: int, g: int, b: int, w: int) -> int:
    """Pack RGBW bytes into Quilt's int32 color code (0xRRGGBBWW)."""
    return (r << 24) | (g << 16) | (b << 8) | w


def _decode_rgbw(code: int) -> tuple[int, int, int, int]:
    """Unpack Quilt's int32 color code to (R, G, B, W) bytes."""
    r = (code >> 24) & 0xFF
    g = (code >> 16) & 0xFF
    b = (code >> 8) & 0xFF
    w = code & 0xFF
    return r, g, b, w


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light entities from a config entry."""
    coordinator: QuiltCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data

    entities = [QuiltLightEntity(coordinator, idu.id) for idu in snapshot.indoor_units]
    async_add_entities(entities)


class QuiltLightEntity(QuiltEntity, LightEntity):
    """Light entity representing an indoor unit's LED light."""

    _attr_color_mode: ColorMode = ColorMode.RGBW
    _attr_translation_key: str = "light"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator)
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_idu_light_{idu_id}"
        self._attr_name: str | None = "LED"
        self._attr_supported_color_modes: set[ColorMode] = {ColorMode.RGBW}

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
        return self._idu.led_on

    @property
    @override
    def brightness(self) -> int | None:
        return round(self._idu.controls.led_brightness * 255)

    @property
    @override
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        return _decode_rgbw(self._idu.controls.led_color_code)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgbw = kwargs.get(ATTR_RGBW_COLOR)

        brightness_pct = (brightness / 255) if brightness is not None else None
        color_code = _encode_rgbw(*rgbw) if rgbw is not None else None

        # Note: Library does not yet support explicit led_state ON/OFF
        # in set_indoor_unit. We control it via brightness and color code.
        target_brightness = brightness_pct
        if target_brightness is None and self.brightness == 0:
            target_brightness = 1.0

        await self.coordinator.client.set_indoor_unit(
            self._idu,
            led_brightness=target_brightness,
            led_color_code=color_code,
        )
        await self.coordinator.async_request_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        # Note: Library does not yet support explicit led_state ON/OFF
        # in set_indoor_unit.
        await self.coordinator.client.set_indoor_unit(
            self._idu,
            led_brightness=0.0,
        )
        await self.coordinator.async_request_refresh()
