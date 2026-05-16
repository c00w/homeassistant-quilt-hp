# Changelog

## [Unreleased]

### Added
- README banner image (`images/banner.svg`) and top-of-page banner block

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
