"""HA-backed token store for the Quilt Heat Pump integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from quilt_hp.tokens import CachedTokens

_LOGGER = logging.getLogger(__name__)

_STORE_KEY: str = "quilt_hp_tokens"
_STORE_VERSION: int = 1


class HATokenStore:
    """``TokenStore`` backed by Home Assistant's async persistent JSON storage.

    Tokens are keyed by email address so multiple accounts can coexist in a
    single HA installation.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the token store."""
        self._store: Store[dict[str, Any]] = Store(hass, _STORE_VERSION, _STORE_KEY)

    async def load(self, email: str) -> CachedTokens | None:
        """Load cached tokens for *email*, or ``None`` if not present."""
        data: dict[str, Any] = await self._store.async_load() or {}
        entry = data.get(email)
        if entry is None:
            return None
        try:
            return CachedTokens(
                id_token=entry["id_token"],
                refresh_token=entry["refresh_token"],
                expires_at=entry["expires_at"],
            )
        except KeyError:
            _LOGGER.warning("Malformed token cache for %s; will re-authenticate", email)
            return None

    async def save(self, email: str, tokens: CachedTokens) -> None:
        """Persist *tokens* for *email*."""
        data: dict[str, Any] = await self._store.async_load() or {}
        data[email] = {
            "id_token": tokens.id_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        }
        await self._store.async_save(data)
