"""Adds config flow for HDO."""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_BASE, \
    CONF_MAC
from homeassistant.core import callback
from voluptuous import UNDEFINED

from . import DOMAIN, DEFAULT_NAME, VERSION, CONF_WOL_TARGET, CONF_WOL_PORT

_LOGGER = logging.getLogger(__name__)


async def _show_form(self, step, user_input):
    """Configure the form."""
    options = {
        vol.Optional(CONF_HOST,
                     default=user_input[CONF_HOST] if user_input and (CONF_HOST in user_input) else UNDEFINED): str,
        vol.Optional(CONF_NAME,
                     default=user_input[CONF_NAME] if user_input and (CONF_NAME in user_input) else DEFAULT_NAME): str,
        vol.Optional(CONF_MAC,
                     default=user_input[CONF_MAC] if user_input and (CONF_MAC in user_input) else UNDEFINED): str,
        vol.Optional(CONF_WOL_TARGET,
                     default=user_input[CONF_WOL_TARGET] if user_input and (
                                 CONF_WOL_TARGET in user_input) else UNDEFINED): str,
        vol.Optional(CONF_WOL_PORT,
                     default=user_input[CONF_WOL_PORT] if user_input and (
                                 CONF_WOL_PORT in user_input) else UNDEFINED): int,
    }
    return self.async_show_form(step_id=step, data_schema=(vol.Schema(
        options)), errors=self._errors)


@config_entries.HANDLERS.register(DOMAIN)
class HDOFlowHandler(config_entries.ConfigFlow):
    """Config flow for iiyama sicp integration."""

    VERSION = VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._data = {}

    async def async_step_user(self, user_input={}):  # pylint: disable=dangerous-default-value
        """Display the form, then store values and create entry."""
        self._errors = {}
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_HOST]:
                await self.async_set_unique_id(user_input[CONF_HOST])
                # Call next step
                return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)
            else:
                self._errors[CONF_BASE] = CONF_HOST
        return await _show_form(self, "user", self._data)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._data.update(config_entry.data)
        if user_input:
            self._data.update(user_input)
            if self._data[CONF_HOST]:
                return self.async_update_reload_and_abort(config_entry, title=self._data[CONF_NAME], data=self._data)
            else:
                self._errors[CONF_BASE] = CONF_HOST.title()
        return await _show_form(self, "reconfigure", self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        if config_entry.unique_id is None:
            return EmptyOptions(config_entry)
        else:
            return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the configuration."""

    def __init__(self, config_entry):
        """Read the configuration and initialize data."""
        self.config_entry = config_entry
        self._data = dict(config_entry.options)
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display the form, then store values and create entry."""

        if user_input is not None:
            # Update entry
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        else:
            if user_input is None:
                user_input = self.config_entry.data
            self._data.update(user_input)
            return await _show_form(self, "init", user_input)


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
