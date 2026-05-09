"""Tests for QuiltCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.quilt_hp.coordinator import QuiltCoordinator

from .conftest import make_snapshot


@pytest.fixture
def mock_client(monkeypatch):
    """Patch QuiltClient inside coordinator module."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.login = AsyncMock()
    client.get_snapshot = AsyncMock(return_value=make_snapshot())
    client.invalidate_snapshot = MagicMock()

    stream = MagicMock()
    stream.on_space_update = MagicMock()
    stream.on_indoor_unit_update = MagicMock()
    stream.on_outdoor_unit_update = MagicMock()
    stream.on_disconnected = MagicMock()
    stream.start = AsyncMock()
    stream.stop = AsyncMock()
    client.stream.return_value = stream

    with (
        patch(
            "custom_components.quilt_hp.coordinator.QuiltClient", return_value=client
        ),
        patch("custom_components.quilt_hp.coordinator.HATokenStore"),
    ):
        yield client, stream


async def test_async_setup_fetches_snapshot(hass: HomeAssistant, mock_client) -> None:
    """async_setup should login, fetch snapshot, and start stream."""
    client, stream = mock_client
    coordinator = QuiltCoordinator(hass, "user@example.com")
    await coordinator.async_setup()

    client.login.assert_awaited_once()
    client.get_snapshot.assert_awaited_once()
    stream.start.assert_awaited_once()
    assert coordinator.data is not None


async def test_async_shutdown_stops_stream(hass: HomeAssistant, mock_client) -> None:
    """async_shutdown should stop the stream and close the client."""
    client, stream = mock_client
    coordinator = QuiltCoordinator(hass, "user@example.com")
    await coordinator.async_setup()
    await coordinator.async_shutdown()

    stream.stop.assert_awaited_once()
    client.__aexit__.assert_awaited()


async def test_space_update_callback(hass: HomeAssistant, mock_client) -> None:
    """Space stream updates should be applied to the snapshot."""
    _client, _stream = mock_client
    coordinator = QuiltCoordinator(hass, "user@example.com")
    await coordinator.async_setup()

    from .conftest import make_space

    updated_space = make_space(ambient_temp_c=25.0)
    coordinator._on_space_update(updated_space)
    coordinator.data.apply_space.assert_called_once_with(updated_space)


async def test_idu_update_callback(hass: HomeAssistant, mock_client) -> None:
    """IDU stream updates should be applied to the snapshot."""
    _client, _stream = mock_client
    coordinator = QuiltCoordinator(hass, "user@example.com")
    await coordinator.async_setup()

    from .conftest import make_idu

    updated_idu = make_idu()
    coordinator._on_idu_update(updated_idu)
    coordinator.data.apply_indoor_unit.assert_called_once_with(updated_idu)


async def test_polling_fallback(hass: HomeAssistant, mock_client) -> None:
    """_async_update_data should invalidate and re-fetch the snapshot."""
    client, _stream = mock_client
    coordinator = QuiltCoordinator(hass, "user@example.com")
    await coordinator.async_setup()

    new_snapshot = make_snapshot()
    client.get_snapshot.return_value = new_snapshot

    result = await coordinator._async_update_data()
    client.invalidate_snapshot.assert_called()
    assert result is new_snapshot
