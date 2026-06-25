"""DataUpdateCoordinator for the Quilt Heat Pump integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
import contextlib
from datetime import UTC, datetime, time as dt_time, timedelta
import logging
from typing import Any, override

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from quilt_hp import QuiltClient  # type: ignore[attr-defined]
from quilt_hp.exceptions import QuiltError
from quilt_hp.models.controller import Controller
from quilt_hp.models.indoor_unit import IndoorUnit
from quilt_hp.models.outdoor_unit import OutdoorUnit
from quilt_hp.models.qsm import QuiltSmartModule
from quilt_hp.models.sensor import ControllerRemoteSensor, RemoteSensor
from quilt_hp.models.space import Space
from quilt_hp.models.system import ComfortSetting, Location, SystemSnapshot

from .const import (
    CONF_POLLING_INTERVAL,
    COORDINATOR_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ENERGY_STATISTICS_LOOKBACK_DAYS,
    ENERGY_UPDATE_INTERVAL_MINUTES,
)
from .token_store import HATokenStore

_LOGGER = logging.getLogger(__name__)

# Number of consecutive stream errors before raising a HA repair issue.
_STREAM_ERROR_THRESHOLD: int = 5
_ISSUE_STREAM_DEGRADED: str = "stream_degraded"


def _latest_valid_bucket_value(buckets: Iterable[Any]) -> float | None:
    """Energy of the most recent valid (non-NaN) hourly bucket, or None."""
    latest_start: datetime | None = None
    latest_value: float | None = None
    for bucket in buckets:
        value = bucket.energy_kwh_or_none
        if value is None:
            continue
        if latest_start is None or bucket.start_time > latest_start:
            latest_start = bucket.start_time
            latest_value = value
    return latest_value


def _energy_statistic_metadata(statistic_id: str) -> StatisticMetaData:
    """Build recorder statistics metadata for a space energy sensor."""
    return StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=None,
        source="recorder",
        statistic_id=statistic_id,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        unit_class=None,
    )


class QuiltCoordinator(DataUpdateCoordinator[SystemSnapshot]):
    """Manages the QuiltClient connection and drives entity updates.

    Initial state is fetched via ``get_snapshot()`` on setup, then
    a ``NotifierStream`` pushes real-time diffs directly into the
    coordinator's data. A periodic poll acts as a fallback only.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        email: str,
        system_id: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        poll_minutes: int = entry.options.get(
            CONF_POLLING_INTERVAL, COORDINATOR_UPDATE_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=poll_minutes),
        )
        token_store = HATokenStore(hass)
        self._client: QuiltClient = QuiltClient(email, token_store=token_store)
        self._system_id: str | None = system_id  # None → library picks default
        self._stream: Any = None  # Using Any for stream due to dynamic library types
        self._stream_error_count: int = 0
        self._was_available: bool = True  # Track connection state for logging
        self.spaces_by_id: dict[str, Space] = {}
        self.idu_by_id: dict[str, IndoorUnit] = {}
        self.idu_by_space_id: dict[str, IndoorUnit] = {}
        self.odu_by_id: dict[str, OutdoorUnit] = {}
        self.ctrl_by_id: dict[str, Controller] = {}
        self.qsm_by_id: dict[str, QuiltSmartModule] = {}
        self.cs_by_id: dict[str, ComfortSetting] = {}
        self.cs_by_space_id: dict[str, list[ComfortSetting]] = {}
        self.remote_sensor_by_id: dict[str, RemoteSensor] = {}
        self.ctrl_remote_sensor_by_id: dict[str, ControllerRemoteSensor] = {}
        self.location_by_id: dict[str, Location] = {}
        # Energy data — updated at most every ENERGY_UPDATE_INTERVAL_MINUTES.
        # Maps space id → most recent valid hourly bucket value (kWh).
        self.energy_hourly_by_space_id: dict[str, float] = {}
        self._energy_last_fetch: datetime | None = None

    @override
    def async_set_updated_data(self, data: SystemSnapshot) -> None:
        """Update the coordinator data and refresh the indexed lookups."""
        self.spaces_by_id = {s.id: s for s in data.spaces}
        self.idu_by_id = {u.id: u for u in data.indoor_units}
        self.idu_by_space_id = {u.space_id: u for u in data.indoor_units if u.space_id}
        self.odu_by_id = {u.id: u for u in data.outdoor_units}
        self.ctrl_by_id = {c.id: c for c in data.controllers}
        self.qsm_by_id = {q.id: q for q in data.quilt_smart_modules}
        self.cs_by_id = {cs.id: cs for cs in data.comfort_settings}
        cs_by_space: dict[str, list[ComfortSetting]] = {}
        for cs in data.comfort_settings:
            cs_by_space.setdefault(cs.space_id, []).append(cs)
        self.cs_by_space_id = cs_by_space
        self.remote_sensor_by_id = {rs.id: rs for rs in data.remote_sensors}
        self.ctrl_remote_sensor_by_id = {
            crs.id: crs for crs in data.controller_remote_sensors
        }
        self.location_by_id = {loc.id: loc for loc in data.locations}

        super().async_set_updated_data(data)

    def _on_stream_error(self, err: object) -> None:
        """Handle a stream error, surfacing a repair issue after repeated failures."""
        # Log once when stream becomes unavailable
        if self._stream_error_count == 0 and self._was_available:
            _LOGGER.warning("Quilt stream connection lost: %s", err)
            self._was_available = False

        self._stream_error_count += 1
        _LOGGER.debug(
            "Quilt stream error (%d); will reconnect: %s",
            self._stream_error_count,
            err,
        )
        if self._stream_error_count >= _STREAM_ERROR_THRESHOLD:
            async_create_issue(
                self.hass,
                DOMAIN,
                _ISSUE_STREAM_DEGRADED,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="stream_degraded",
            )

    def _on_stream_reconnect(self) -> None:
        """Clear the stream error counter and resolve any open repair issue."""
        if self._stream_error_count > 0:
            # Log once when stream is restored
            if not self._was_available:
                _LOGGER.info("Quilt stream connection restored")
                self._was_available = True
            self._stream_error_count = 0
            async_delete_issue(self.hass, DOMAIN, _ISSUE_STREAM_DEGRADED)

    # ------------------------------------------------------------------
    # Public API used by __init__.py
    # ------------------------------------------------------------------

    @property
    def client(self) -> QuiltClient:
        """Expose the underlying QuiltClient for entity write operations."""
        return self._client

    @property
    def stream_error_count(self) -> int:
        """Return the number of consecutive stream errors since last reconnect."""
        return self._stream_error_count

    @property
    def is_streaming(self) -> bool:
        """Return True when the gRPC stream is active.

        Entities use this to skip ``async_request_refresh()`` after writes —
        the stream delivers state changes within milliseconds, making an
        immediate poll redundant.
        """
        return self._stream is not None

    async def async_set_space(self, space: Space, **kwargs: Any) -> Space:
        """Set space fields with one transparent auth-refresh retry."""
        return await self._with_auth_retry(
            lambda: self._client.set_space(space, **kwargs)
        )

    async def async_set_indoor_unit(
        self, indoor_unit: IndoorUnit, **kwargs: Any
    ) -> IndoorUnit:
        """Set indoor unit fields with one transparent auth-refresh retry."""
        return await self._with_auth_retry(
            lambda: self._client.set_indoor_unit(indoor_unit, **kwargs)
        )

    async def async_set_schedule_execution(self, *, paused: bool) -> None:
        """Pause or resume all schedules with one transparent auth-refresh retry."""
        await self._with_auth_retry(
            lambda: self._client.set_schedule_execution(paused=paused)
        )

    async def async_setup(self) -> None:
        """Open gRPC channel, login, fetch initial snapshot, start stream."""
        _ = await self._client.__aenter__()
        try:
            await self._client.login()

            snapshot = await self._client.get_snapshot(system_id=self._system_id)
            self.async_set_updated_data(snapshot)

            await self._async_update_energy()
            await self._start_stream(snapshot)
        except Exception:
            # Close the client if any setup step fails to avoid resource leaks.
            with contextlib.suppress(Exception):
                _ = await self._client.__aexit__(None, None, None)
            raise

    @override
    async def async_shutdown(self) -> None:
        """Stop the stream and close the gRPC channel."""
        if self._stream is not None:
            with contextlib.suppress(BaseException):
                await self._stream.stop()
            self._stream = None

        with contextlib.suppress(Exception):
            _ = await self._client.__aexit__(None, None, None)

    # ------------------------------------------------------------------
    # Stream management
    # ------------------------------------------------------------------

    async def _start_stream(self, snapshot: SystemSnapshot) -> None:
        topics = snapshot.stream_topics()
        stream = self._client.stream(topics, max_reconnects=-1)
        stream.on_space_update(self._on_space_update)
        stream.on_indoor_unit_update(self._on_idu_update)
        stream.on_outdoor_unit_update(self._on_odu_update)
        stream.on_controller_update(self._on_ctrl_update)
        stream.on_qsm_update(self._on_qsm_update)
        stream.on_remote_sensor_update(self._on_remote_sensor_update)
        stream.on_controller_remote_sensor_update(self._on_ctrl_remote_sensor_update)
        stream.on_error(self._on_stream_error)
        await stream.start()
        # Only assign after successful start so async_shutdown doesn't try to
        # stop a stream that never began.
        self._stream = stream

    def _on_space_update(self, space: Space) -> None:
        if self.data:
            _ = self.data.apply_space(space)
            # Targeted index update — avoids rebuilding all 6 dicts on every tick.
            self.spaces_by_id[space.id] = space
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_idu_update(self, idu: IndoorUnit) -> None:
        if self.data:
            _ = self.data.apply_indoor_unit(idu)
            self.idu_by_id[idu.id] = idu
            if idu.space_id:
                self.idu_by_space_id[idu.space_id] = idu
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_odu_update(self, odu: OutdoorUnit) -> None:
        if self.data:
            _ = self.data.apply_outdoor_unit(odu)
            self.odu_by_id[odu.id] = odu
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_ctrl_update(self, ctrl: Controller) -> None:
        if self.data:
            _ = self.data.apply_controller(ctrl)
            self.ctrl_by_id[ctrl.id] = ctrl
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_qsm_update(self, qsm: QuiltSmartModule) -> None:
        if self.data:
            _ = self.data.apply_qsm(qsm)
            self.qsm_by_id[qsm.id] = qsm
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_remote_sensor_update(self, rs: RemoteSensor) -> None:
        if self.data:
            _ = self.data.apply_remote_sensor(rs)
            self.remote_sensor_by_id[rs.id] = rs
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    def _on_ctrl_remote_sensor_update(self, crs: ControllerRemoteSensor) -> None:
        if self.data:
            _ = self.data.apply_controller_remote_sensor(crs)
            self.ctrl_remote_sensor_by_id[crs.id] = crs
            self._on_stream_reconnect()
            self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Polling fallback
    # ------------------------------------------------------------------

    @override
    async def _async_update_data(self) -> SystemSnapshot:
        try:
            self._client.invalidate_snapshot()
            snapshot = await self._client.get_snapshot(  # type: ignore[no-any-return]
                system_id=self._system_id
            )

            # Log once when connection is restored
            if not self._was_available:
                _LOGGER.info("Quilt connection restored")
                self._was_available = True

        except Exception as err:
            # Log once when connection is lost
            if self._was_available:
                _LOGGER.warning("Quilt connection lost: %s", err)
                self._was_available = False
            raise UpdateFailed(f"Error fetching Quilt snapshot: {err}") from err

        await self._async_update_energy()
        return snapshot  # type: ignore[no-any-return]

    async def _async_update_energy(self) -> None:
        """Fetch energy metrics from the API, rate-limited, and refresh stats.

        Each fetch re-queries from the start of yesterday through now and
        re-imports the full set of hourly statistics rows for every space
        sensor. Because ``async_import_statistics`` overwrites rows keyed by
        ``(statistic_id, start)``, every fetch heals any hour that was
        incomplete when last seen — in particular the final hour of the
        previous day, which a "today"-only query never revisits after a UTC
        midnight rollover. This replaces the earlier rollover-only correction.
        """
        now = datetime.now(UTC)
        today_start = datetime.combine(now.date(), dt_time.min, tzinfo=UTC)
        if (
            self._energy_last_fetch is not None
            and now - self._energy_last_fetch
            < timedelta(minutes=ENERGY_UPDATE_INTERVAL_MINUTES)
        ):
            return

        # Look back so the previous day's final (often incomplete) hour is
        # recomputed after midnight without a dedicated rollover path.
        window_start = today_start - timedelta(days=ENERGY_STATISTICS_LOOKBACK_DAYS)
        try:
            metrics = await self._client.get_energy(
                window_start, now, system_id=self._system_id
            )
        except Exception as err:
            _LOGGER.warning("Failed to fetch Quilt energy data: %s", err)
            return

        # Live sensor value: the most recent valid hourly bucket per space.
        self.energy_hourly_by_space_id = {
            m.space_id: value
            for m in metrics
            if (value := _latest_valid_bucket_value(m.buckets)) is not None
        }
        self._energy_last_fetch = now

        await self._async_import_energy_statistics(metrics)

    async def _async_import_energy_statistics(self, metrics: Iterable[Any]) -> None:
        """Re-import hourly long-term statistics for each space sensor.

        For each space, walks its hourly buckets in order and writes one
        statistics row per valid bucket, continuing the cumulative ``sum`` from
        the value recorded just before the window. Re-importing every fetch
        lets later, more-complete data overwrite earlier partial hours.
        """
        ent_reg = er.async_get(self.hass)
        for metric in metrics:
            # Mirrors QuiltEnergyHourlySensor's unique_id in sensor.py.
            unique_id = f"quilt_space_{metric.space_id}_energy_hourly"
            statistic_id = ent_reg.async_get_entity_id(
                SENSOR_DOMAIN, DOMAIN, unique_id
            )
            if statistic_id is None:
                continue  # Sensor not registered yet — nothing to attach to.

            buckets = sorted(metric.buckets, key=lambda b: b.start_time)
            if not buckets:
                continue

            running_sum = await self._async_baseline_sum(
                get_instance(self.hass), statistic_id, buckets[0].start_time
            )
            rows: list[StatisticData] = []
            for bucket in buckets:
                value = bucket.energy_kwh_or_none
                if value is None:
                    continue  # NaN/missing hour — leave a gap, keep the sum.
                running_sum += value
                rows.append(
                    StatisticData(
                        start=bucket.start_time, state=value, sum=running_sum
                    )
                )
            if rows:
                async_import_statistics(
                    self.hass, _energy_statistic_metadata(statistic_id), rows
                )

    async def _async_baseline_sum(
        self, recorder: Any, statistic_id: str, window_start: datetime
    ) -> float:
        """Cumulative ``sum`` recorded immediately before ``window_start``.

        Anchors the re-imported rows onto the existing series so the running
        dashboard total stays continuous across fetches. Returns 0.0 when no
        prior statistics exist.
        """
        stats = await recorder.async_add_executor_job(
            statistics_during_period,
            self.hass,
            window_start - timedelta(days=2),
            window_start,
            {statistic_id},
            "hour",
            None,
            {"sum"},
        )
        rows = stats.get(statistic_id)
        if rows and rows[-1].get("sum") is not None:
            return float(rows[-1]["sum"])
        return 0.0

    async def _with_auth_retry[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        """Retry one write after re-login when access token has expired.

        The Quilt library raises ``QuiltError`` for all API failures. We detect
        expired-JWT errors by inspecting the message text.  If the upstream
        library ever exposes a dedicated exception class or error code for auth
        failures, replace this string check with a type/code check.

        Raises ``ConfigEntryAuthFailed`` if the re-login attempt fails,
        triggering HA's reauth flow automatically.
        """
        try:
            return await operation()
        except QuiltError as err:
            if "jwt is expired" not in str(err).lower():
                raise

        # Token expired — attempt re-login once
        try:
            await self._client.login()
        except QuiltError as auth_err:
            _LOGGER.error("Quilt re-authentication failed: %s", auth_err)
            raise ConfigEntryAuthFailed(
                "Quilt authentication failed. Please re-authenticate."
            ) from auth_err

        return await operation()
