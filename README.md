# Quilt Heat Pump — Home Assistant Integration

A Home Assistant custom component for [Quilt](https://www.quilt.com/) mini-split HVAC systems.

Built on top of [`quilt-hp-python`](https://github.com/eman/quilt-hp-python) — a fully-async
gRPC client that communicates directly with the Quilt cloud API.

## Features

- **Climate entities** — control HVAC mode and setpoints for each Quilt space (room)
- **Sensor entities** — ambient temperature, humidity, fan speed, inlet/outlet temps,
  presence level, COP, HVAC power, compressor data, and per-space energy
- **Fan entities** — set indoor unit fan speed (Auto / Quiet / Low / Medium / High / Blast)
- **Light entities** — toggle and dim indoor unit LED, set RGBW color
- **Select entities** — louver mode (Closed / Sweep / Fixed / Auto) and fixed angle
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

Tokens are persisted in HA storage and refreshed automatically. You will only need to
re-authenticate if your refresh token expires.

## Dependencies

- [`quilt-hp-python`](https://pypi.org/project/quilt-hp-python/) — installed automatically by HA.
