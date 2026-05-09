"""Constants for the Quilt Heat Pump integration."""

DOMAIN = "quilt_hp"

CONF_EMAIL = "email"
CONF_SYSTEM_ID = "system_id"
CONF_HOME_NAME = "home_name"

PLATFORMS = ["climate", "fan", "light", "select", "sensor"]

# DataUpdateCoordinator polling fallback interval (seconds)
COORDINATOR_UPDATE_INTERVAL_MINUTES = 5

# Timeout (seconds) for initial snapshot fetch on setup
INITIAL_FETCH_TIMEOUT_S = 20
