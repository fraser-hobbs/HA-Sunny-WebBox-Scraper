"""DataUpdateCoordinator for SMA Sunny WebBox."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SMAWebBoxAPI
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SMAWebBoxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching SMA WebBox data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SMAWebBoxAPI,
        device_key: str,
    ) -> None:
        """Initialize."""
        self.api = api
        self.device_key = device_key

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            data = await self.api.async_get_data(self.device_key)
            if data is None:
                raise UpdateFailed("Failed to fetch data from SMA WebBox")
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
