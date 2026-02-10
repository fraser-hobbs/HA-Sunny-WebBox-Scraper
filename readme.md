# SMA Sunny WebBox Integration for Home Assistant

Monitor your SMA solar inverter via Sunny WebBox with Home Assistant.

## Features

- Real-time DC power, voltage, and current monitoring
- Energy dashboard integration with total and daily energy
- Automatic session management
- Config flow setup (no YAML required)

## Installation via HACS

1. Add this repository to HACS as a custom repository
2. Search for "SMA Sunny WebBox" in HACS
3. Click Install
4. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "SMA Sunny WebBox"
4. Enter:
   - **IP Address**: Your WebBox IP (e.g., `10.0.0.25`)
   - **User Level**: Choose `Installer` or `User`
   - **Password**: Your WebBox password (default installer: `1111`)
   - **Device Key**: Found in WebBox URL (e.g., `131:2120116523:i`)

## Energy Dashboard

The integration provides sensors with `state_class: total_increasing` that work directly with Home Assistant's Energy Dashboard:

1. Go to Settings → Dashboards → Energy
2. Add "Solar Production" → Select "Solar Total Energy"
3. Optionally add "Solar Daily Energy" for daily tracking

## Support

Report issues at: https://github.com/yourusername/sma-sunny-webbox/issues
