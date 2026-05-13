# Quilt Heat Pump — Home Assistant Integration

[![Validate](https://github.com/eman/homeassistant-quilt-hp/actions/workflows/validate.yml/badge.svg)](https://github.com/eman/homeassistant-quilt-hp/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/eman/homeassistant-quilt-hp)](https://github.com/eman/homeassistant-quilt-hp/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom component for [Quilt](https://www.quilt.com/) mini-split HVAC systems.

Built on top of [`quilt-hp-python`](https://github.com/eman/quilt-hp-python) — a fully-async
gRPC client that communicates directly with the Quilt cloud API.

## Features

- **Climate entities** — control HVAC mode and setpoints for each Quilt space (room)
- **Sensor entities** — ambient temperature, humidity, fan speed, inlet/outlet temps,
  presence level, COP, HVAC power, compressor data, and per-space energy
- **Fan entities** — set indoor unit fan speed (Auto / Quiet / Low / Medium / High / Blast)
- **Light entities** — toggle and dim indoor unit LED, set RGBW color and animation effect
- **Select entities** — louver mode (Closed / Sweep / Fixed / Auto) and fixed angle
- **Binary sensor entities** — motion, presence, occupancy, and connectivity status per IDU
- **Switch entities** — pause or resume all Quilt schedules for a location
- **Real-time updates** — powered by Quilt's bidirectional gRPC stream with auto-reconnect
- **Polling fallback** — configurable interval fetch if the stream is unavailable

## Prerequisites

- A [Quilt](https://www.quilt.com/) account with at least one configured system
- Home Assistant 2026.3 or newer
- Python 3.14.2 or newer (managed automatically by HA)

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
   (category: **Integration**, URL: `https://github.com/eman/homeassistant-quilt-hp`).
2. Install **Quilt Heat Pump**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/quilt_hp/` into your HA `config/custom_components/` directory
and restart.

## Configuration

### Initial setup

1. Go to **Settings → Devices & Services → Add Integration** and search for *Quilt*.
2. Enter your Quilt account email address. Quilt will send a one-time passcode (OTP).
3. Enter the OTP to complete authentication.

If your account has **multiple homes**, you will be prompted to select which one to
integrate. Each home can be added as a separate integration entry — just run the setup
flow again and select a different home.

### Options

After setup, click **Configure** on the integration card to adjust:

| Option | Default | Range | Description |
|---|---|---|---|
| Polling interval | 5 min | 1–60 min | How often to fall back to polling if the real-time stream is unavailable |

### Re-authentication

If your session expires, HA will raise a re-authentication notification. Follow the
prompt to re-enter your email and a new OTP. No other settings are changed.

## Entities

The following entities are created per device. Entities marked *Disabled* are off by
default to reduce noise; enable them individually in the HA entity registry.

### Per location (home)

| Entity | Platform | Default | Notes |
|---|---|---|---|
| Schedules | `switch` | Enabled | Pauses or resumes all Quilt schedules for the home. Off = paused. |

### Per space (room) — on the IDU device

| Entity | Platform | Default |
|---|---|---|
| Climate | `climate` | Enabled |
| Space Temperature | `sensor` | Enabled |

The climate entity supports the following HVAC modes: **Off**, **Cool**, **Heat**,
**Heat/Cool** (auto), **Fan only**. It also exposes Quilt **comfort settings** as HA
preset modes — selecting a preset activates that comfort profile on the space.

### Per Indoor Unit (IDU)

| Entity | Platform | Default |
|---|---|---|
| Fan Speed | `fan` | Enabled |
| LED Light | `light` | Enabled |
| Louver Mode | `select` | Enabled |
| Louver Angle | `select` | Enabled |
| Temperature (IDU sensor) | `sensor` | Enabled |
| Humidity | `sensor` | Enabled |
| Fan Speed RPM | `sensor` | Enabled |
| Motion | `binary_sensor` | Enabled |
| Presence | `binary_sensor` | Enabled |
| Occupied | `binary_sensor` | Enabled |
| Inlet Temperature | `sensor` | Disabled |
| Outlet Temperature | `sensor` | Disabled |
| Presence Level | `sensor` | Disabled |
| HVAC Capacity | `sensor` | Disabled |
| HVAC Power | `sensor` | Disabled |
| COP | `sensor` | Disabled |
| Calibrated Temperature | `sensor` | Disabled |
| Motion Signal (radar) | `sensor` | Disabled |
| Presence Signal (radar) | `sensor` | Disabled |
| Illuminance | `sensor` | Disabled |
| Online | `binary_sensor` | Disabled |

### Per Outdoor Unit (ODU)

| Entity | Platform | Default |
|---|---|---|
| Outdoor Temperature | `sensor` | Enabled |
| Compressor Frequency | `sensor` | Disabled |
| High-Side Pressure | `sensor` | Disabled |
| Low-Side Pressure | `sensor` | Disabled |

### Per Controller (Quilt Dial)

| Entity | Platform | Default |
|---|---|---|
| Temperature | `sensor` | Enabled |
| Online | `binary_sensor` | Disabled |
| WiFi Signal | `sensor` | Disabled |

## Troubleshooting

### Enable debug logging

Add the following to your `config/configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: warning
  logs:
    custom_components.quilt_hp: debug
```

Logs are written to `home-assistant.log` in your HA config directory.

### Common issues

**Entities become unavailable after a few hours**
The gRPC stream disconnected and the reconnect failed. Check debug logs for
`NotifierStream` errors. Ensure your HA host has outbound internet access to the Quilt
cloud API.

**Re-authentication loop**
Your refresh token has expired. Complete the re-auth flow from the HA notification. If
the issue persists, remove and re-add the integration.

**OTP not accepted**
The OTP expires quickly. Make sure you enter it within a minute or two of receiving it.
If the config flow times out between the email and OTP steps, restart the flow.

### Filing issues

Please open an issue at [github.com/eman/homeassistant-quilt-hp/issues](https://github.com/eman/homeassistant-quilt-hp/issues)
and include:
- Home Assistant version
- Integration version
- Relevant lines from `home-assistant.log` with debug logging enabled

## Contributing

### Development setup

```bash
git clone https://github.com/eman/homeassistant-quilt-hp
cd homeassistant-quilt-hp
pip install -r requirements-dev.txt
```

### Running tests and checks

```bash
pytest                        # run all tests
ruff check . && ruff format --check .   # lint + format
mypy custom_components/quilt_hp         # type check
basedpyright custom_components/quilt_hp # type check
```

### Local Home Assistant instance

A `docker-compose.yml` is included for running a real HA instance against the
integration locally:

```bash
docker compose up -d       # start
docker compose restart     # pick up integration changes
docker compose down        # stop
```

HA is available at **http://localhost:8124**.

## Dependencies

- [`quilt-hp-python`](https://pypi.org/project/quilt-hp-python/) — installed automatically by HA.

## License

MIT License. See [LICENSE](LICENSE) for details.

This project is not affiliated with or endorsed by Quilt.
