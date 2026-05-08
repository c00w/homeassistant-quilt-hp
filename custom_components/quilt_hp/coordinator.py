"""DataUpdateCoordinator for the Quilt Heat Pump integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from quilt_hp import QuiltClient
from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.space import Space
from quilt_hp.models.system import SystemSnapshot

from .const import COORDINATOR_UPDATE_INTERVAL_MINUTES, DOMAIN
from .token_store import HATokenStore

_LOGGER = logging.getLogger(__name__)


class QuiltCoordinator(DataUpdateCoordinator[SystemSnapshot]):
    """Manages the QuiltClient connection and drives entity updates.

    Initial state is fetched via ``get_snapshot()`` on setup, then
    a ``NotifierStream`` pushes real-time diffs directly into the
    coordinator's data. A periodic poll acts as a fallback only.
    """

    def __init__(self, hass: HomeAssistant, email: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=COORDINATOR_UPDATE_INTERVAL_MINUTES),
        )
        token_store = HATokenStore(hass)
        self._client = QuiltClient(email, token_store=token_store)
        self._stream = None

    # ------------------------------------------------------------------
    # Public API used by __init__.py
    # ------------------------------------------------------------------

    @property
    def client(self) -> QuiltClient:
        """Expose the underlying QuiltClient for entity write operations."""
        return self._client

    async def async_setup(self) -> None:
        """Open gRPC channel, login, fetch initial snapshot, start stream."""
        await self._client.__aenter__()
        await self._client.login()

        snapshot = await self._client.get_snapshot()
        self.async_set_updated_data(snapshot)

        await self._start_stream(snapshot)

    async def async_shutdown(self) -> None:
        """Stop the stream and close the gRPC channel."""
        if self._stream is not None:
            try:
                await self._stream.stop()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Error stopping Quilt stream", exc_info=True)
            self._stream = None

        try:
            await self._client.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Error closing Quilt client", exc_info=True)

    # ------------------------------------------------------------------
    # Stream management
    # ------------------------------------------------------------------

    async def _start_stream(self, snapshot: SystemSnapshot) -> None:
        topics = snapshot.stream_topics()
        self._stream = self._client.stream(topics, max_reconnects=-1)
        self._stream.on_space_update(self._on_space_update)
        self._stream.on_indoor_unit_update(self._on_idu_update)
        self._stream.on_outdoor_unit_update(self._on_odu_update)
        self._stream.on_disconnected(
            lambda: _LOGGER.warning("Quilt stream disconnected; will reconnect")
        )
        await self._stream.start()

    def _on_space_update(self, space: Space) -> None:
        if self.data is not None:
            self.data.apply_space(space)
            self.async_set_updated_data(self.data)

    def _on_idu_update(self, idu: IndoorUnit) -> None:
        if self.data is not None:
            self.data.apply_indoor_unit(idu)
            self.async_set_updated_data(self.data)

    def _on_odu_update(self, odu: OutdoorUnit) -> None:
        if self.data is not None:
            self.data.apply_outdoor_unit(odu)
            self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Polling fallback
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> SystemSnapshot:
        try:
            self._client.invalidate_snapshot()
            return await self._client.get_snapshot()
        except Exception as err:
            raise UpdateFailed(f"Error fetching Quilt snapshot: {err}") from err
