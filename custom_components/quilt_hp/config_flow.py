"""Config flow for the Quilt Heat Pump integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from quilt_hp import QuiltClient
from quilt_hp.exceptions import QuiltAuthError

from .const import CONF_EMAIL, DOMAIN
from .token_store import HATokenStore

_LOGGER = logging.getLogger(__name__)


class _AwaitingOTP(Exception):
    """Sentinel: interrupts the login coroutine while the user enters the OTP."""


class QuiltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step config flow: email → OTP → done."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._client: QuiltClient | None = None

    # ------------------------------------------------------------------
    # Step 1: collect the email address and trigger the OTP send
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect email and initiate OTP delivery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip().lower()

            # Prevent duplicate entries for the same account.
            await self.async_set_unique_id(self._email)
            self._abort_if_unique_id_configured()

            token_store = HATokenStore(self.hass)
            self._client = QuiltClient(self._email, token_store=token_store)

            try:
                await self._client.__aenter__()
                # Passing _send_otp causes the library to send the challenge
                # email and then raise _AwaitingOTP before blocking for input.
                await self._client.login(otp_callback=self._send_otp)
            except _AwaitingOTP:
                # Expected path — OTP email sent, move to next step.
                return await self.async_step_otp()
            except QuiltAuthError:
                errors["base"] = "cannot_connect"
                await self._cleanup_client()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error initiating Quilt login")
                errors["base"] = "unknown"
                await self._cleanup_client()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_EMAIL): str}),
            errors=errors,
        )

    async def _send_otp(self, email: str) -> str:  # noqa: ARG002
        """Called by QuiltClient.login() to collect the OTP.

        Raises ``_AwaitingOTP`` to pause the login coroutine; the actual code
        will be supplied in ``async_step_otp``.
        """
        raise _AwaitingOTP

    # ------------------------------------------------------------------
    # Step 2: collect the OTP and complete authentication
    # ------------------------------------------------------------------

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect OTP and finish login."""
        errors: dict[str, str] = {}

        if user_input is not None:
            otp = user_input["otp"].strip()
            try:
                await self._client.login(otp_callback=lambda _: otp)  # type: ignore[union-attr]
            except QuiltAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error completing Quilt OTP login")
                errors["base"] = "unknown"
            else:
                await self._cleanup_client()
                return self.async_create_entry(
                    title=self._email,
                    data={CONF_EMAIL: self._email},
                )

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    # ------------------------------------------------------------------
    # Re-authentication flow (token expired)
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Re-authentication entry point — prefill email and re-run OTP flow."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry:
            self._email = entry.data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show re-auth confirmation form (email is pre-filled)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token_store = HATokenStore(self.hass)
            self._client = QuiltClient(self._email, token_store=token_store)
            try:
                await self._client.__aenter__()
                await self._client.login(otp_callback=self._send_otp)
            except _AwaitingOTP:
                return await self.async_step_otp()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Re-auth OTP trigger failed")
                errors["base"] = "cannot_connect"
                await self._cleanup_client()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _cleanup_client(self) -> None:
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
            self._client = None
