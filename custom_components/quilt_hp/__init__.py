"""Home Assistant integration entry point for Quilt Heat Pump."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_EMAIL, DOMAIN, INITIAL_FETCH_TIMEOUT_S, PLATFORMS
from .coordinator import QuiltCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Quilt Heat Pump from a config entry."""
    email: str = entry.data[CONF_EMAIL]
    coordinator = QuiltCoordinator(hass, email)

    try:
        async with asyncio.timeout(INITIAL_FETCH_TIMEOUT_S):
            await coordinator.async_setup()
    except asyncio.TimeoutError as err:
        raise ConfigEntryNotReady("Timed out fetching initial Quilt snapshot") from err
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(f"Quilt setup failed: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_shutdown)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Quilt Heat Pump config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
