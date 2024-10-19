"""Adds config flow for HDO."""
import logging
from collections import OrderedDict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_FORCE_UPDATE, CONF_HOST, CONF_BASE, \
    CONF_MAC, CONF_PORT
from homeassistant.core import callback

from . import DOMAIN, DEFAULT_NAME, CONF_REFRESH_RATE, CONF_MAX_COUNT, VERSION, CONF_WOL_TARGET

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

    async def _show_user_form(self, user_input):
        """Configure the form."""
        # Defaults
        host = ""
        if user_input is not None and CONF_HOST in user_input:
            host = user_input[CONF_HOST]
        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_HOST, default=host)] = str
        data_schema[vol.Optional(CONF_NAME, default=DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_FORCE_UPDATE, default=True)] = bool
        data_schema[vol.Optional(CONF_REFRESH_RATE, default=86400)] = int
        data_schema[vol.Optional(CONF_MAC)] = str
        data_schema[vol.Optional(CONF_PORT)] = int
        data_schema[vol.Optional(CONF_WOL_TARGET)] = str
        data_schema[vol.Optional(CONF_MAX_COUNT, default=5)] = int
        form = self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors)
        return form

    async def async_step_import(self, user_input):  # pylint: disable=unused-argument
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

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
            self._data[CONF_CODE] = self.config_entry.unique_id
            if CONF_REFRESH_RATE in user_input:
                self._data[CONF_REFRESH_RATE] = user_input[CONF_REFRESH_RATE]
            return self.async_create_entry(title=self._data[CONF_CODE], data=self._data)
        else:
            return await self._show_init_form(user_input)

    async def _show_init_form(self, user_input):
        """Configure the form."""
        if user_input is None:
            user_input = self.config_entry.data
        data_schema = OrderedDict()
        data_schema[
            vol.Optional(CONF_NAME, default=user_input[CONF_NAME] if CONF_NAME in user_input else DEFAULT_NAME)] = str
        data_schema[vol.Optional(CONF_FORCE_UPDATE, default=user_input[
            CONF_FORCE_UPDATE] if CONF_FORCE_UPDATE in user_input else True)] = bool
        data_schema[vol.Optional(CONF_REFRESH_RATE, default=user_input[
            CONF_REFRESH_RATE] if CONF_REFRESH_RATE in user_input else 86400)] = int
        data_schema[vol.Optional(CONF_MAX_COUNT,
                                 default=user_input[CONF_MAX_COUNT] if CONF_MAX_COUNT in user_input else 5)] = int
        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema), errors=self._errors)


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
