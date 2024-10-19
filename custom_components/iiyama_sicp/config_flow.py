"""Adds config flow for HDO."""
import logging
from collections import OrderedDict

import getmac
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_BASE, \
    CONF_MAC, CONF_PORT
from homeassistant.core import callback, HomeAssistant

from . import DOMAIN, DEFAULT_NAME, CONF_REFRESH_RATE, VERSION, CONF_WOL_TARGET

_LOGGER = logging.getLogger(__name__)


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
            if user_input[CONF_HOST] != "":
                # Remember Frequency
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._data.update(user_input)
                for c in [CONF_REFRESH_RATE, CONF_MAC, CONF_PORT, CONF_WOL_TARGET]:
                    if c in user_input:
                        self._data[c] = user_input[c]

                # Call next step
                return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)
            else:
                self._errors[CONF_BASE] = CONF_HOST.title()
        return await self._show_user_form(user_input)

    async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
        """Migrate old entry."""
        data = {**config_entry.data}
        if not data[CONF_MAC]:
            data[CONF_MAC] = getmac.get_mac_address(ip=data[CONF_HOST], hostname=data[CONF_HOST])
            hass.config_entries.async_update_entry(config_entry, data=data, minor_version=1, version=1)
        return True

    async def _show_user_form(self, user_input):
        """Configure the form."""
        # Defaults
        host = ""
        if user_input is not None and CONF_HOST in user_input:
            host = user_input[CONF_HOST]
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_HOST, default=host)] = str
        data_schema[vol.Optional(CONF_NAME, default=DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_MAC)] = str
        data_schema[vol.Optional(CONF_PORT)] = int
        data_schema[vol.Optional(CONF_WOL_TARGET)] = str
        form = self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors)
        return form

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
            return await self._show_init_form(user_input)

    async def _show_init_form(self, user_input):
        """Configure the form."""
        if user_input is None:
            user_input = self.config_entry.data
        data_schema = OrderedDict()
        data_schema[
            vol.Optional(CONF_NAME, default=user_input[CONF_NAME] if CONF_NAME in user_input else DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_HOST, default=user_input[CONF_HOST] if CONF_HOST in user_input else None)] = str
        data_schema[vol.Optional(CONF_PORT, default=user_input[CONF_PORT] if CONF_PORT in user_input else 5000)] = int
        data_schema[vol.Optional(CONF_MAC, default=user_input[CONF_MAC] if CONF_MAC in user_input else None)] = str
        data_schema[vol.Optional(CONF_WOL_TARGET,
                                 default=user_input[CONF_WOL_TARGET] if CONF_WOL_TARGET in user_input else None)] = str
        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema), errors=self._errors)


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
