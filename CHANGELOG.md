# Changelog

## [Unreleased]

## [0.3.0] - 2026-05-16

### Fixed
- `CancelledError` (a `BaseException` in Python 3.11+) now correctly suppressed when cancelling the in-flight login task and when stopping the gRPC stream; previously it propagated and caused unhandled exceptions
- `coordinator.async_setup()` now closes the API client if stream setup fails, preventing a resource leak
- Energy window start date now derived from the UTC clock (`now.date()`) instead of `date.today()` (local time), preventing off-by-one errors on servers not running in UTC
- Config flow home selection now disambiguates duplicate home names with numeric suffixes (e.g. "Home (2)") so users can distinguish between homes with identical names
- `HATokenStore.load()` now handles malformed persisted data (wrong type, missing keys) gracefully instead of crashing with `TypeError` or `AttributeError`
- `normalize_temperature()` now handles non-float numeric inputs (e.g. `int`) without raising `TypeError`

### Added
- Test coverage raised from 82% to 97% (252 tests)
- **Entity category assignments (Gold tier)**: Diagnostic sensors now properly categorized
  - Battery, signal strength, online status → DIAGNOSTIC
  - Performance metrics (COP, RPM, pressures, etc.) → DIAGNOSTIC
  - Radar/ALS sensors → DIAGNOSTIC
  - WiFi/PCB diagnostics → DIAGNOSTIC
  - Primary sensors (temperature, humidity, power) remain uncategorized for dashboard prominence
- **Silver tier compliance**: Integration now meets Home Assistant Silver tier requirements
  - Smart connection state logging (log once on loss, once on restore)
  - PARALLEL_UPDATES constants to prevent overwhelming devices
  - Comprehensive documentation with troubleshooting guide
  - Enhanced configuration and installation instructions
- **Reconfigure step** in config flow to allow changing email or re-authenticating without removing integration
- **Entity translations**: All entity names now use translation_key for better internationalization support
- **Error handling improvements**: Added ConfigEntryAuthFailed exception for automatic reauth flow
- **Quality scale documentation**: Added quality_scale.yaml documenting Bronze tier compliance
- **Comprehensive error tests**: Added test_error_handling.py with tests for auth failures, stream errors, and network issues
- More specific error messages in config flow (network_error, invalid_email, otp_expired, api_error)
- README banner image (`images/banner.svg`) and top-of-page banner block
- README link to `quilt-hp-python` docs for protocol, streaming, and feature details

### Changed
- **Device naming improved** to follow Home Assistant best practices. Indoor unit devices now use their configured name (e.g., "Living Room IDU") instead of just the room name, eliminating confusion between device names and area names. Outdoor units now include serial numbers when available for better identification.
- Removed duplicate `_attr_name` settings in favor of `_attr_translation_key` for consistent i18n
- Stream error logging changed from WARNING on every error to single WARNING on loss + single INFO on restore
- Polling fallback now logs connection state transitions instead of every failure

## [0.2.0] - 2026-05-13

### Added
- Energy consumption sensors (power, accumulated energy) for indoor and outdoor units
- Schedule switch entity to enable/disable Quilt scheduling per space
- Comprehensive sensor coverage: space, IDU, ODU, QSM (radar/ALS), and Controller entities
- Controller (Quilt Dial) device with temperature sensor
- Multi-home selection step in config flow
- Brand assets (`icon.png`, `logo.png`, `icon.svg`, `logo.svg`) for HA brands API
- Docker Compose setup for local HA development and testing
- HACS validation GitHub Actions workflow (`hacs/action` + `hassfest`)

### Changed
- Integration display name renamed from "Quilt Heat Pump" to "Quilt"
- Spaces mapped to HA Areas (`suggested_area`) instead of devices; IDU is the primary device per room
- Outdoor unit linked to its indoor unit via `via_device` for correct HA device hierarchy
- ODU sensors created per IDU connection to support multi-IDU scenarios
- Upgraded minimum requirement to `quilt-hp-python>=0.3.0`
- Minimum Home Assistant version set to 2026.3.0

### Fixed
- OTP login flow: keep login task alive across config flow steps to prevent OTP rejection
- Louver angle availability check uses `louver_mode` instead of `louver_fixed_position`
- Louver angle select always returns a valid option
- Outdoor unit linking uses `space_id` relationship
- IDU device model uses `hardware_id` instead of `settings.name`
- `NotifierStream` uses `on_error` callback (replaces non-existent `on_disconnected`)
- All strict mypy and basedpyright type errors resolved

## [0.1.0] - 2025-01-01

### Added
- Initial implementation of the Quilt Heat Pump Home Assistant integration
- OTP-based config flow (email → one-time passcode)
- Climate entity for each Space (HVAC mode, setpoints, current temperature)
- Fan entity for each IndoorUnit (fan speed, oscillation)
- Light entity for each IndoorUnit LED indicator
- Select entity for louver position control
- Binary sensor entities for IndoorUnit state
- Real-time updates via `NotifierStream` gRPC bidirectional stream
- Polling fallback every 5 minutes via `DataUpdateCoordinator`
- JWT token persistence via `HATokenStore` (HA `Storage` API)
- Automatic token refresh with transparent re-login on expiry

[Unreleased]: https://github.com/eman/homeassistant-quilt-hp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/eman/homeassistant-quilt-hp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/eman/homeassistant-quilt-hp/releases/tag/v0.1.0
