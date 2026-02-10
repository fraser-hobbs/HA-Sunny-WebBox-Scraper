"""Config flow for SMA Sunny WebBox integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_USER_LEVEL, CONF_DEVICE_KEY, USER_LEVELS
from .api import SMAWebBoxAPI

_LOGGER = logging.getLogger(__name__)


class SMAWebBoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA Sunny WebBox."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Test connection
            api = SMAWebBoxAPI(
                host=user_input[CONF_HOST],
                password=user_input[CONF_PASSWORD],
                user_level=user_input[CONF_USER_LEVEL],
            )

            try:
                if await api.async_test_connection():
                    # Create unique ID based on host
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()

                    # Store data for next step
                    self.context["user_input"] = user_input
                    return await self.async_step_device()
                else:
                    errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USER_LEVEL, default="installer"): vol.In(
                    USER_LEVELS
                ),
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_device(self, user_input=None):
        """Handle device key configuration."""
        errors = {}

        if user_input is not None:
            # Combine with previous step data
            config_data = {**self.context["user_input"], **user_input}

            return self.async_create_entry(
                title=f"SMA WebBox ({config_data[CONF_HOST]})",
                data=config_data,
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_KEY, default="131:2120116523:i"
                ): str,
            }
        )

        return self.async_show_form(
            step_id="device",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "host": self.context["user_input"][CONF_HOST]
            },
        )
