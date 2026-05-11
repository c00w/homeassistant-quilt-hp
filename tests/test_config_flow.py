"""Tests for the config flow."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.quilt_hp.const import CONF_EMAIL, DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture
def mock_quilt_client():
    """Patch QuiltClient used by the config flow."""

    with patch("custom_components.quilt_hp.config_flow.QuiltClient") as mock_cls:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        async def mock_login(otp_callback=None):
            """Mock login matching quilt-hp-python 0.2.2 callback pattern.
            
            Simulates the OTP flow by calling the callback and waiting
            for the OTP to be provided via the returned future.
            """
            if otp_callback:
                # Call the callback, which returns a future that we await
                otp_future = await otp_callback("send otp")
                # OTP was provided (by the test via _otp_future.set_result)
                # Simulate successful login after OTP
                return None
            else:
                # No callback means cached token or no OTP needed
                return None

        client.login = AsyncMock(side_effect=mock_login)
        mock_cls.return_value = client
        yield client


async def test_user_step_shows_form(hass: HomeAssistant) -> None:
    """Step 1 should render the email form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_user_step_proceeds_to_otp(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Valid email should proceed to the OTP step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "otp"


async def test_otp_step_creates_entry(hass: HomeAssistant, mock_quilt_client) -> None:
    """Valid OTP should create the config entry (single home path)."""
    sys = MagicMock()
    sys.id = "sys-001"
    sys.name = "My Home"
    mock_quilt_client.list_systems = AsyncMock(return_value=[sys])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "123456"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Home"
    assert result["data"] == {
        "email": "user@example.com",
        "system_id": "sys-001",
        "home_name": "My Home",
    }


async def test_multi_home_shows_selector(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """When multiple homes exist, a home selection step should be shown."""
    s1 = MagicMock()
    s1.id = "sys-001"
    s1.name = "Primary Home"

    s2 = MagicMock()
    s2.id = "sys-002"
    s2.name = "Vacation Home"

    mock_quilt_client.list_systems = AsyncMock(return_value=[s1, s2])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "123456"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "home"


async def test_multi_home_creates_entry_for_chosen_home(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Selecting a home should create an entry with the correct system_id."""
    s1 = MagicMock()
    s1.id = "sys-001"
    s1.name = "Primary Home"

    s2 = MagicMock()
    s2.id = "sys-002"
    s2.name = "Vacation Home"

    mock_quilt_client.list_systems = AsyncMock(return_value=[s1, s2])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "123456"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"home_name": "Vacation Home"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["system_id"] == "sys-002"
    assert result["title"] == "Vacation Home"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
async def test_otp_invalid_auth_shows_error(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Bad OTP should surface an invalid_auth error."""
    from quilt_hp.exceptions import QuiltAuthError

    async def mock_login_with_error(otp_callback=None):
        """Mock login that raises QuiltAuthError on bad OTP."""
        if otp_callback:
            await otp_callback("ignored")
            raise QuiltAuthError("bad otp")

    mock_quilt_client.login = AsyncMock(side_effect=mock_login_with_error)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "654321"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_cannot_connect_error(hass: HomeAssistant) -> None:
    """Connection failure should surface a cannot_connect error."""
    from quilt_hp.exceptions import QuiltAuthError

    with patch("custom_components.quilt_hp.config_flow.QuiltClient") as mock_cls:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.login = AsyncMock(side_effect=QuiltAuthError("no network"))
        mock_cls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"
