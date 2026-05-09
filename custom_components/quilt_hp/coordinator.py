"""DataUpdateCoordinator for the Quilt Heat Pump integration."""

from __future__ import annotations

import contextlib
from datetime import timedelta
import logging
from typing import Any, override

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from quilt_hp import QuiltClient  # type: ignore[attr-defined]
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

    def __init__(
        self, hass: HomeAssistant, email: str, system_id: str | None = None
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=COORDINATOR_UPDATE_INTERVAL_MINUTES),
        )
        token_store = HATokenStore(hass)
        self._client: QuiltClient = QuiltClient(email, token_store=token_store)
        self._system_id: str | None = system_id  # None → library picks default
        self._stream: Any = None  # Using Any for stream due to dynamic library types
        self.spaces_by_id: dict[str, Space] = {}
        self.idu_by_id: dict[str, IndoorUnit] = {}
        self.odu_by_id: dict[str, OutdoorUnit] = {}

    @override
    def async_set_updated_data(self, data: SystemSnapshot) -> None:
        """Update the coordinator data and refresh the indexed lookups."""
        self.spaces_by_id = {s.id: s for s in data.spaces}
        self.idu_by_id = {u.id: u for u in data.indoor_units}
        self.odu_by_id = {u.id: u for u in data.outdoor_units}
        super().async_set_updated_data(data)

    # ------------------------------------------------------------------
    # Public API used by __init__.py
    # ------------------------------------------------------------------

    @property
    def client(self) -> QuiltClient:
        """Expose the underlying QuiltClient for entity write operations."""
        return self._client

    async def async_setup(self) -> None:
        """Open gRPC channel, login, fetch initial snapshot, start stream."""
        _ = await self._client.__aenter__()
        await self._client.login()

        snapshot = await self._client.get_snapshot(system_id=self._system_id)
        self.async_set_updated_data(snapshot)

        await self._start_stream(snapshot)

    @override
    async def async_shutdown(self) -> None:
        """Stop the stream and close the gRPC channel."""
        if self._stream is not None:
            with contextlib.suppress(Exception):
                await self._stream.stop()
            self._stream = None

        with contextlib.suppress(Exception):
            _ = await self._client.__aexit__(None, None, None)

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
        if self.data:
            _ = self.data.apply_space(space)
            self.async_set_updated_data(self.data)

    def _on_idu_update(self, idu: IndoorUnit) -> None:
        if self.data:
            _ = self.data.apply_indoor_unit(idu)
            self.async_set_updated_data(self.data)

    def _on_odu_update(self, odu: OutdoorUnit) -> None:
        if self.data:
            _ = self.data.apply_outdoor_unit(odu)
            self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Polling fallback
    # ------------------------------------------------------------------

    @override
    async def _async_update_data(self) -> SystemSnapshot:
        try:
            self._client.invalidate_snapshot()
            return await self._client.get_snapshot(system_id=self._system_id)
        except Exception as err:
            raise UpdateFailed(f"Error fetching Quilt snapshot: {err}") from err
