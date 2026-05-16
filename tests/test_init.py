"""Tests for the __init__ module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
import pytest

from custom_components.quilt_hp import async_setup_entry, async_unload_entry


async def test_async_setup_entry_success(hass) -> None:
    """Test successful setup of a config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {"email": "test@example.com", "system_id": "test_system"}
    entry.async_on_unload = MagicMock(return_value=None)
    entry.add_update_listener = MagicMock(return_value=None)

    with patch("custom_components.quilt_hp.QuiltCoordinator") as mock_coord_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_setup = AsyncMock()
        mock_coordinator.async_shutdown = AsyncMock()
        mock_coord_class.return_value = mock_coordinator

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new=AsyncMock()
        ):
            result = await async_setup_entry(hass, entry)
            assert result is True
            mock_coordinator.async_setup.assert_awaited_once()


async def test_async_setup_entry_timeout(hass) -> None:
    """Test setup failure due to timeout."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {"email": "test@example.com", "system_id": "test_system"}

    async def slow_setup():
        """Simulate a slow setup."""
        import asyncio

        await asyncio.sleep(100)

    with patch("custom_components.quilt_hp.QuiltCoordinator") as mock_coord_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_setup = AsyncMock(side_effect=slow_setup)
        mock_coord_class.return_value = mock_coordinator

        with pytest.raises(ConfigEntryNotReady, match="Timed out"):
            await async_setup_entry(hass, entry)


async def test_async_setup_entry_failure(hass) -> None:
    """Test setup failure due to exception."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {"email": "test@example.com", "system_id": "test_system"}

    with patch("custom_components.quilt_hp.QuiltCoordinator") as mock_coord_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_setup = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_coord_class.return_value = mock_coordinator

        with pytest.raises(ConfigEntryNotReady, match="Quilt setup failed"):
            await async_setup_entry(hass, entry)


async def test_async_unload_entry(hass) -> None:
    """Test unloading a config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    with patch.object(
        hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)
    ):
        result = await async_unload_entry(hass, entry)
        assert result is True


async def test_async_migrate_entry_v1(hass) -> None:
    """Test migration for v1 (no-op)."""
    from custom_components.quilt_hp import async_migrate_entry

    entry = MagicMock(spec=ConfigEntry)
    entry.version = 1

    result = await async_migrate_entry(hass, entry)
    assert result is True


async def test_async_migrate_entry_unknown_version(hass) -> None:
    """Test migration failure for unknown version."""
    from custom_components.quilt_hp import async_migrate_entry

    entry = MagicMock(spec=ConfigEntry)
    entry.version = 999

    result = await async_migrate_entry(hass, entry)
    assert result is False
