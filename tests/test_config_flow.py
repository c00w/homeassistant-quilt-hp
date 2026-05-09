"""Tests for the Quilt Heat Pump config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.quilt_hp.config_flow import _AwaitingOTP
from custom_components.quilt_hp.const import CONF_EMAIL, DOMAIN


@pytest.fixture
def mock_quilt_client():
    """Patch QuiltClient used by the config flow."""
    with patch(
        "custom_components.quilt_hp.config_flow.QuiltClient"
    ) as mock_cls:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.login = AsyncMock(side_effect=_AwaitingOTP)
        client.list_systems = AsyncMock(
            return_value=[MagicMock(id="sys-001", name="My Home")]
        )
        mock_cls.return_value = client
        yield client


async def test_user_step_shows_form(hass: HomeAssistant) -> None:
    """Step 1 should render the email form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


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
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "otp"


async def test_otp_step_creates_entry(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Valid OTP should create the config entry (single home path)."""
    mock_quilt_client.login = AsyncMock(
        side_effect=[_AwaitingOTP, None]  # first call raises, second succeeds
    )
    mock_quilt_client.list_systems = AsyncMock(
        return_value=[MagicMock(id="sys-001", name="My Home")]
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    # Now on OTP step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "123456"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_EMAIL] == "user@example.com"
    assert result["data"]["system_id"] == "sys-001"


async def test_multi_home_shows_selector(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """When multiple homes exist, a home selection step should be shown."""
    mock_quilt_client.login = AsyncMock(side_effect=[_AwaitingOTP, None])
    mock_quilt_client.list_systems = AsyncMock(
        return_value=[
            MagicMock(id="sys-001", name="Primary Home"),
            MagicMock(id="sys-002", name="Vacation Home"),
        ]
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "123456"}
    )
    # Should land on the home selection step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "home"


async def test_multi_home_creates_entry_for_chosen_home(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Selecting a home should create an entry with the correct system_id."""
    mock_quilt_client.login = AsyncMock(side_effect=[_AwaitingOTP, None])
    mock_quilt_client.list_systems = AsyncMock(
        return_value=[
            MagicMock(id="sys-001", name="Primary Home"),
            MagicMock(id="sys-002", name="Vacation Home"),
        ]
    )

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
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["system_id"] == "sys-002"
    assert result["data"]["home_name"] == "Vacation Home"
    assert result["title"] == "Vacation Home"


async def test_otp_invalid_auth_shows_error(
    hass: HomeAssistant, mock_quilt_client
) -> None:
    """Bad OTP should surface an invalid_auth error."""
    from quilt_hp.exceptions import QuiltAuthError

    mock_quilt_client.login = AsyncMock(
        side_effect=[_AwaitingOTP, QuiltAuthError("bad otp")]
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_EMAIL: "user@example.com"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"otp": "wrong"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_cannot_connect_error(hass: HomeAssistant) -> None:
    """Connection failure should surface a cannot_connect error."""
    from quilt_hp.exceptions import QuiltAuthError

    with patch(
        "custom_components.quilt_hp.config_flow.QuiltClient"
    ) as mock_cls:
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
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"
