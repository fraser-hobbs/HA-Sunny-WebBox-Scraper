"""The SMA Sunny WebBox integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .api import SMAWebBoxAPI
from .const import DOMAIN, CONF_USER_LEVEL, CONF_DEVICE_KEY
from .coordinator import SMAWebBoxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMA Sunny WebBox from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = SMAWebBoxAPI(
        host=entry.data[CONF_HOST],
        password=entry.data[CONF_PASSWORD],
        user_level=entry.data[CONF_USER_LEVEL],
    )

    coordinator = SMAWebBoxCoordinator(
        hass=hass,
        api=api,
        device_key=entry.data[CONF_DEVICE_KEY],
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
