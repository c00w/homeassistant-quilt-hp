"""Regression tests for bugs found during comprehensive audit."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest
from quilt_hp.exceptions import QuiltError
from quilt_hp.models.enums import HVACMode as QHVACMode

from custom_components.quilt_hp.coordinator import QuiltCoordinator
from custom_components.quilt_hp.sensor import IDU_SENSOR_DESCRIPTIONS
from custom_components.quilt_hp.utils import normalize_temperature

from .conftest import make_idu, make_mock_coordinator, make_snapshot, make_space


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: normalize_temperature crashes on non-float numeric (int)
# File: utils.py:14
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeTemperature:
    def test_none_returns_none(self) -> None:
        assert normalize_temperature(None) is None

    def test_nan_returns_none(self) -> None:
        assert normalize_temperature(float("nan")) is None

    def test_normal_float(self) -> None:
        assert normalize_temperature(21.5) == 21.5

    def test_int_value_does_not_crash(self) -> None:
        """Bug fix: math.isnan(int) raises TypeError on some versions."""
        assert normalize_temperature(21) == 21  # type: ignore[arg-type]

    def test_non_numeric_returns_none(self) -> None:
        """If API sends unexpected type, return None instead of crashing."""
        assert normalize_temperature("bad") is None  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: date.today() vs UTC mismatch in energy window
# File: coordinator.py:324
# ═══════════════════════════════════════════════════════════════════════════════


def _make_entry_mock() -> MagicMock:
    entry = MagicMock()
    entry.options = {}
    return entry


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.login = AsyncMock()
    client.get_snapshot = AsyncMock(return_value=make_snapshot())
    client.invalidate_snapshot = MagicMock()
    client.get_energy = AsyncMock(return_value=[])

    stream = MagicMock()
    stream.on_space_update = MagicMock()
    stream.on_indoor_unit_update = MagicMock()
    stream.on_outdoor_unit_update = MagicMock()
    stream.on_controller_update = MagicMock()
    stream.on_qsm_update = MagicMock()
    stream.on_remote_sensor_update = MagicMock()
    stream.on_controller_remote_sensor_update = MagicMock()
    stream.on_error = MagicMock()
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


class TestEnergyDateBug:
    """The energy window start must use UTC date, not local date."""

    async def test_energy_start_uses_utc_date(
        self, hass: HomeAssistant, mock_client
    ) -> None:
        client, _stream = mock_client
        coordinator = QuiltCoordinator(hass, _make_entry_mock(), "u@e.com")
        await coordinator.async_setup()

        # Force stale so energy fetch actually runs
        coordinator._energy_last_fetch = datetime.now(UTC) - timedelta(hours=1)

        metric = SimpleNamespace(space_id="space-001", total_kwh=2.0)
        client.get_energy = AsyncMock(return_value=[metric])

        await coordinator._async_update_energy()

        # Verify the start arg is a UTC-aware datetime with midnight time
        call_args = client.get_energy.call_args
        start_arg = call_args[0][0]
        assert start_arg.tzinfo == UTC
        assert start_arg.hour == 0
        assert start_arg.minute == 0
        # The date should be from UTC, not local
        assert start_arg.date() == datetime.now(UTC).date()


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: async_setup leaks client on partial failure
# File: coordinator.py:193-202
# ═══════════════════════════════════════════════════════════════════════════════


class TestSetupResourceLeak:
    async def test_client_closed_on_login_failure(
        self, hass: HomeAssistant, mock_client
    ) -> None:
        client, _stream = mock_client
        client.login = AsyncMock(side_effect=QuiltError("login failed"))

        coordinator = QuiltCoordinator(hass, _make_entry_mock(), "u@e.com")
        with pytest.raises(QuiltError):
            await coordinator.async_setup()

        client.__aexit__.assert_awaited()

    async def test_client_closed_on_snapshot_failure(
        self, hass: HomeAssistant, mock_client
    ) -> None:
        client, _stream = mock_client
        client.get_snapshot = AsyncMock(side_effect=Exception("snapshot failed"))

        coordinator = QuiltCoordinator(hass, _make_entry_mock(), "u@e.com")
        with pytest.raises(Exception, match="snapshot failed"):
            await coordinator.async_setup()

        client.__aexit__.assert_awaited()

    async def test_client_closed_on_stream_failure(
        self, hass: HomeAssistant, mock_client
    ) -> None:
        client, stream = mock_client
        stream.start = AsyncMock(side_effect=Exception("stream start failed"))

        coordinator = QuiltCoordinator(hass, _make_entry_mock(), "u@e.com")
        with pytest.raises(Exception, match="stream start failed"):
            await coordinator.async_setup()

        client.__aexit__.assert_awaited()


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: token_store only catches KeyError
# File: token_store.py:42-50
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenStoreRobustness:
    async def test_load_handles_type_error(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.token_store import HATokenStore

        store = HATokenStore(hass)
        # Simulate malformed data where entry is a list instead of a dict
        with patch.object(store._store, "async_load", return_value={"user@x.com": [1, 2, 3]}):
            result = await store.load("user@x.com")
            assert result is None

    async def test_load_handles_attribute_error(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.token_store import HATokenStore

        store = HATokenStore(hass)
        # Entry is a string instead of a dict
        with patch.object(store._store, "async_load", return_value={"user@x.com": "bad"}):
            result = await store.load("user@x.com")
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: sensor presence_detection_level * 100 crashes when None
# File: sensor.py:160
# ═══════════════════════════════════════════════════════════════════════════════


class TestPresenceLevelNoneGuard:
    def test_presence_level_none_returns_none(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.sensor import QuiltIDUSensor

        idu = make_idu()
        idu.state.presence_detection_level = None
        snapshot = make_snapshot(indoor_units=[idu])
        coordinator = make_mock_coordinator(hass, snapshot)

        desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "presence_level")
        entity = QuiltIDUSensor(coordinator, "idu-001", desc)
        # Should return None, not crash with TypeError
        assert entity.native_value is None

    def test_presence_level_with_value(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.sensor import QuiltIDUSensor

        idu = make_idu()
        idu.state.presence_detection_level = 0.5
        snapshot = make_snapshot(indoor_units=[idu])
        coordinator = make_mock_coordinator(hass, snapshot)

        desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "presence_level")
        entity = QuiltIDUSensor(coordinator, "idu-001", desc)
        assert entity.native_value == 50.0


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: module power None energy_measurement_j
# File: sensor.py:287-288
# ═══════════════════════════════════════════════════════════════════════════════


class TestModulePowerNoneGuard:
    def test_module_power_none_energy(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.sensor import QuiltIDUSensor

        idu = make_idu()
        idu.performance_data = SimpleNamespace(
            measurement_interval_s=5.0,
            energy_measurement_j=None,
            # other fields not used by this sensor
            coil_temperature_c=10.0,
            gas_pipe_temperature_c=30.0,
            liquid_pipe_temperature_c=25.0,
            inlet_humidity_pct=50.0,
        )
        snapshot = make_snapshot(indoor_units=[idu])
        coordinator = make_mock_coordinator(hass, snapshot)

        desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "module_power")
        entity = QuiltIDUSensor(coordinator, "idu-001", desc)
        assert entity.native_value is None

    def test_module_power_none_interval(self, hass: HomeAssistant) -> None:
        from custom_components.quilt_hp.sensor import QuiltIDUSensor

        idu = make_idu()
        idu.performance_data = SimpleNamespace(
            measurement_interval_s=None,
            energy_measurement_j=1000.0,
            coil_temperature_c=10.0,
            gas_pipe_temperature_c=30.0,
            liquid_pipe_temperature_c=25.0,
            inlet_humidity_pct=50.0,
        )
        snapshot = make_snapshot(indoor_units=[idu])
        coordinator = make_mock_coordinator(hass, snapshot)

        desc = next(d for d in IDU_SENSOR_DESCRIPTIONS if d.key == "module_power")
        entity = QuiltIDUSensor(coordinator, "idu-001", desc)
        assert entity.native_value is None


# ═══════════════════════════════════════════════════════════════════════════════
# Bug: duplicate home names in config flow cause ambiguous selection
# File: config_flow.py:203-220
# ═══════════════════════════════════════════════════════════════════════════════


pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class TestDuplicateHomeNames:
    async def test_duplicate_names_disambiguated(
        self, hass: HomeAssistant
    ) -> None:
        """Two homes with the same name should get unique labels."""
        from custom_components.quilt_hp.const import CONF_EMAIL, CONF_HOME_NAME, DOMAIN

        with patch("custom_components.quilt_hp.config_flow.QuiltClient") as mock_cls:
            client = MagicMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)

            async def mock_login(otp_callback=None):
                if otp_callback:
                    await otp_callback("send otp")

            client.login = AsyncMock(side_effect=mock_login)

            s1 = SimpleNamespace(id="sys-001", name="Home")
            s2 = SimpleNamespace(id="sys-002", name="Home")
            client.list_systems = AsyncMock(return_value=[s1, s2])
            mock_cls.return_value = client

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={"otp": "123456"}
            )
            # Should show home selection with disambiguated labels
            assert result["step_id"] == "home"

            # Select the second home using its disambiguated label
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_HOME_NAME: "Home (2)"}
            )
            assert result["type"].value == "create_entry"
            assert result["data"]["system_id"] == "sys-002"
            assert result["data"]["home_name"] == "Home"
