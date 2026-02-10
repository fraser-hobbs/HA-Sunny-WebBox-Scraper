"""Constants for SMA Sunny WebBox integration."""
from datetime import timedelta

DOMAIN = "sma_sunny_webbox"
CONF_HOST = "host"
CONF_PASSWORD = "password"
CONF_USER_LEVEL = "user_level"
CONF_DEVICE_KEY = "device_key"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

USER_LEVELS = {
    "user": "User",
    "installer": "Installer"
}

# Sensor types - Energy Dashboard compatible
SENSOR_TYPES = {
    "ac_power": {
        "name": "AC Power",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:solar-power",
    },
    "dc_power": {
        "name": "DC Power",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:solar-panel",
    },
    "dc_voltage": {
        "name": "DC Voltage",
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "icon": "mdi:lightning-bolt",
    },
    "dc_current": {
        "name": "DC Current",
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "icon": "mdi:current-dc",
    },
    "total_energy": {
        "name": "Total Energy",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Required for Energy Dashboard
        "icon": "mdi:lightning-bolt-circle",
    },
    "daily_energy": {
        "name": "Daily Energy",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Required for Energy Dashboard
        "icon": "mdi:solar-power-variant",
    },
}
