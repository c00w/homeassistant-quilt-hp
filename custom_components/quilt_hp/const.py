"""Constants for the Quilt Heat Pump integration."""

DOMAIN = "quilt_hp"

CONF_EMAIL = "email"

PLATFORMS = ["climate", "fan", "light", "select", "sensor"]

# DataUpdateCoordinator polling fallback interval (seconds)
COORDINATOR_UPDATE_INTERVAL_MINUTES = 5

# Timeout (seconds) for initial snapshot fetch on setup
INITIAL_FETCH_TIMEOUT_S = 20
