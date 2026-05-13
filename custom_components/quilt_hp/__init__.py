"""Home Assistant integration entry point for Quilt Heat Pump."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_EMAIL,
    CONF_SYSTEM_ID,
    INITIAL_FETCH_TIMEOUT_S,
    PLATFORMS,
)
from .coordinator import QuiltCoordinator

_LOGGER = logging.getLogger(__name__)

# Typed config entry — avoids hass.data lookups in all platform setups.
type QuiltConfigEntry = ConfigEntry[QuiltCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to the current version.

    V1 is the only version that has ever existed. This stub is here so that
    future migrations have a well-defined starting point.
    """
    _LOGGER.debug(
        "Migrating Quilt config entry from version %s to %s",
        entry.version,
        1,
    )
    if entry.version == 1:
        return True

    _LOGGER.error(
        "Cannot migrate Quilt config entry from unknown version %s", entry.version
    )
    return False


async def async_setup_entry(hass: HomeAssistant, entry: QuiltConfigEntry) -> bool:
    """Set up Quilt Heat Pump from a config entry."""
    email: str = entry.data[CONF_EMAIL]
    system_id: str | None = entry.data.get(CONF_SYSTEM_ID)
    coordinator = QuiltCoordinator(hass, entry, email, system_id=system_id)

    try:
        async with asyncio.timeout(INITIAL_FETCH_TIMEOUT_S):
            await coordinator.async_setup()
    except TimeoutError as err:
        raise ConfigEntryNotReady("Timed out fetching initial Quilt snapshot") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Quilt setup failed: {err}") from err

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_shutdown)

    async def _async_reload_on_options_update(
        hass: HomeAssistant, entry: QuiltConfigEntry
    ) -> None:
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_update))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: QuiltConfigEntry) -> bool:
    """Unload a Quilt Heat Pump config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
