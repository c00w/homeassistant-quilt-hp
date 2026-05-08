"""Light platform for Quilt Heat Pump — one entity per IndoorUnit (LED)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.enums import LedAnimation, LightState

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

    entities = [
        QuiltLightEntity(coordinator, idu.id)
        for idu in snapshot.indoor_units
    ]
    async_add_entities(entities)


class QuiltLightEntity(QuiltEntity, LightEntity):
    """Light entity representing an indoor unit's LED light."""

    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_translation_key = "light"

    def __init__(self, coordinator: QuiltCoordinator, idu_id: str) -> None:
        super().__init__(coordinator)
        self._idu_id = idu_id
        self._attr_unique_id = f"quilt_idu_light_{idu_id}"
        self._attr_name = "LED"

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
        return self._idu.led_on

    @property
    def brightness(self) -> int | None:
        return round(self._idu.controls.led_brightness * 255)

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        return _decode_rgbw(self._idu.controls.led_color_code)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgbw = kwargs.get(ATTR_RGBW_COLOR)

        brightness_pct = (brightness / 255) if brightness is not None else None
        color_code = _encode_rgbw(*rgbw) if rgbw is not None else None

        await self.coordinator.client.set_indoor_unit(
            self._idu,
            led_state=LightState.ON,
            led_brightness=brightness_pct,
            led_color_code=color_code,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_indoor_unit(
            self._idu,
            led_state=LightState.OFF,
        )
        await self.coordinator.async_request_refresh()
