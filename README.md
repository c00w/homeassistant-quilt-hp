# Quilt Heat Pump — Home Assistant Integration

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
- **Real-time updates** — powered by Quilt's bidirectional gRPC stream with auto-reconnect
- **Polling fallback** — 5-minute interval fetch if the stream is unavailable

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS.
2. Install **Quilt Heat Pump**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/quilt_hp/` into your HA `config/custom_components/` directory
and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration** and search for *Quilt Heat Pump*.
2. Enter your Quilt account email address. Quilt will send a one-time passcode.
3. Enter the OTP to complete setup.

If your account has **multiple homes**, you will be prompted to select which one to integrate.
Each home can be added as a separate integration entry — just run the setup flow again and
choose a different home.

Tokens are persisted in HA storage and refreshed automatically. You will only need to
re-authenticate if your refresh token expires.

## Entities

The following entities are created for each device. Entities marked *disabled* are off by
default to reduce noise; enable them individually in the HA entity registry.

### Per space (room) — on the IDU device

| Entity | Platform | Default |
|---|---|---|
| Climate (HVAC mode + setpoints) | `climate` | ✅ Enabled |
| Space Temperature | `sensor` | ✅ Enabled |

### Per Indoor Unit (IDU)

| Entity | Platform | Default |
|---|---|---|
| Fan Speed | `fan` | ✅ Enabled |
| LED Light | `light` | ✅ Enabled |
| Louver Mode | `select` | ✅ Enabled |
| Louver Angle | `select` | ✅ Enabled |
| Temperature (IDU sensor) | `sensor` | ✅ Enabled |
| Humidity | `sensor` | ✅ Enabled |
| Fan Speed RPM | `sensor` | ✅ Enabled |
| Motion | `binary_sensor` | ✅ Enabled |
| Presence | `binary_sensor` | ✅ Enabled |
| Occupied | `binary_sensor` | ✅ Enabled |
| Inlet Temperature | `sensor` | ⬜ Disabled |
| Outlet Temperature | `sensor` | ⬜ Disabled |
| Presence Level | `sensor` | ⬜ Disabled |
| HVAC Capacity | `sensor` | ⬜ Disabled |
| HVAC Power | `sensor` | ⬜ Disabled |
| COP | `sensor` | ⬜ Disabled |
| Calibrated Temperature | `sensor` | ⬜ Disabled |
| Motion Signal (radar) | `sensor` | ⬜ Disabled |
| Presence Signal (radar) | `sensor` | ⬜ Disabled |
| Illuminance | `sensor` | ⬜ Disabled |
| Online | `binary_sensor` | ⬜ Disabled |

### Per Outdoor Unit (ODU)

| Entity | Platform | Default |
|---|---|---|
| Outdoor Temperature | `sensor` | ✅ Enabled |
| Compressor Frequency | `sensor` | ⬜ Disabled |
| High-Side Pressure | `sensor` | ⬜ Disabled |
| Low-Side Pressure | `sensor` | ⬜ Disabled |

### Per Controller (Quilt Dial)

| Entity | Platform | Default |
|---|---|---|
| Temperature | `sensor` | ✅ Enabled |
| Online | `binary_sensor` | ⬜ Disabled |
| WiFi Signal | `sensor` | ⬜ Disabled |

## Dependencies

- [`quilt-hp-python`](https://pypi.org/project/quilt-hp-python/) — installed automatically by HA.
