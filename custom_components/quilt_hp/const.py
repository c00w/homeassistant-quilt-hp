"""Constants for the Quilt Heat Pump integration."""

from homeassistant.const import Platform

DOMAIN = "quilt_hp"

CONF_EMAIL = "email"
CONF_SYSTEM_ID = "system_id"
CONF_HOME_NAME = "home_name"
CONF_POLLING_INTERVAL = "polling_interval"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# DataUpdateCoordinator polling fallback interval (minutes) — default and bounds.
COORDINATOR_UPDATE_INTERVAL_MINUTES = 5
COORDINATOR_UPDATE_INTERVAL_MIN = 1
COORDINATOR_UPDATE_INTERVAL_MAX = 60

# How often energy data is refreshed from the API (minutes).
ENERGY_UPDATE_INTERVAL_MINUTES = 30

# How far back each energy fetch re-queries and re-imports hourly statistics.
# A one-day lookback makes the window span two calendar days — the whole
# previous day plus the current day so far — so every fetch rewrites both with
# fresh hourly data points. This recomputes the previous day's final (often
# incomplete) hour after a UTC midnight rollover with no dedicated code path.
ENERGY_STATISTICS_LOOKBACK_DAYS = 1

# Timeout (seconds) for initial snapshot fetch on setup
INITIAL_FETCH_TIMEOUT_S = 20
