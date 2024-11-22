import json
import logging
import os
import typing

import getmac
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_NAME, CONF_FORCE_UPDATE, CONF_HOST, CONF_MAC, Platform, CONF_DOMAIN)
from homeassistant.core import HomeAssistant
from voluptuous import ALLOW_EXTRA

from custom_components.iiyama_sicp.coordinator import SicpUpdateCoordinator
from custom_components.iiyama_sicp.pyamasicp.client import Client

CONF_WOL_TARGET: typing.Final = "wol_target"
CONF_WOL_PORT: typing.Final = "wol_port"
CONF_MAX_COUNT = 'maxCount'
CONF_REFRESH_RATE = 'refreshRate'

_LOGGER = logging.getLogger(__name__)
_LOGGER.info('Starting iiyama_sicp')

MANIFEST = json.load(open("%s/manifest.json" % os.path.dirname(os.path.realpath(__file__))))
VERSION = MANIFEST["version"]
DOMAIN = MANIFEST[CONF_DOMAIN]
DEFAULT_NAME = MANIFEST[CONF_NAME]
PLATFORMS = [Platform.MEDIA_PLAYER]
ISSUE_URL = "https://github.com/konikvranik/hacs_iiyama_tv/issues"

SCHEMA = {
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_MAC): cv.string,
    vol.Required(CONF_WOL_TARGET): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_FORCE_UPDATE, default=True): cv.boolean,
    vol.Optional(CONF_REFRESH_RATE, default=86400): vol.All(vol.Coerce(int)),
    vol.Optional(CONF_MAX_COUNT, default=5): vol.All(vol.Coerce(int)),
}

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up ESPHome binary sensors based on a config entry."""

    coordinator_ = SicpUpdateCoordinator(hass, config_entry, Client(config_entry.data.get(CONF_HOST)))
    config_entry.runtime_data = {'coordinator': coordinator_}
    await coordinator_.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    data = {**config_entry.data}
    if not (CONF_MAC in data and data[CONF_MAC]):
        data[CONF_MAC] = getmac.get_mac_address(ip=data[CONF_HOST], hostname=data[CONF_HOST])
        hass.config_entries.async_update_entry(config_entry, data=data, minor_version=1, version=1)
    return True
