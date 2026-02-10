"""DataUpdateCoordinator for SMA Sunny WebBox with retry logic."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from .api import SMAWebBoxAPI
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SMAWebBoxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching SMA WebBox data with retry logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SMAWebBoxAPI,
        device_key: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize."""
        self.api = api
        self.device_key = device_key
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API with retry logic."""
        try:
            data = await self.api.async_get_data(self.device_key)

            if data is None:
                self._consecutive_failures += 1
                _LOGGER.warning(
                    "Failed to fetch data from SMA WebBox (attempt %d/%d)",
                    self._consecutive_failures,
                    self._max_consecutive_failures
                )

                if self._consecutive_failures >= self._max_consecutive_failures:
                    raise UpdateFailed(
                        f"Failed to fetch data after {self._max_consecutive_failures} attempts"
                    )

                # Return last known data if available
                if self.data:
                    _LOGGER.debug("Returning last known data")
                    return self.data

                raise UpdateFailed("No data available from SMA WebBox")

            # Reset failure counter on success
            if self._consecutive_failures > 0:
                _LOGGER.info("Successfully reconnected to SMA WebBox")
            self._consecutive_failures = 0

            return data

        except UpdateFailed:
            raise
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error(
                "Unexpected error communicating with API (attempt %d/%d): %s",
                self._consecutive_failures,
                self._max_consecutive_failures,
                err
            )

            if self._consecutive_failures >= self._max_consecutive_failures:
                raise UpdateFailed(f"Error communicating with API: {err}")

            # Return last known data if available
            if self.data:
                return self.data

            raise UpdateFailed(f"Error communicating with API: {err}")

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh with special handling."""
        try:
            await super().async_config_entry_first_refresh()
        except UpdateFailed as err:
            raise ConfigEntryNotReady(f"Failed to connect to SMA WebBox: {err}") from err

    def update_scan_interval(self, scan_interval: int) -> None:
        """Update the scan interval."""
        self.update_interval = timedelta(seconds=scan_interval)
        _LOGGER.info("Updated scan interval to %d seconds", scan_interval)
