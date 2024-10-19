import json
import logging
import os
import typing

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_NAME, CONF_FORCE_UPDATE, CONF_HOST, CONF_MAC, Platform, CONF_DOMAIN)
from homeassistant.core import HomeAssistant
from voluptuous import ALLOW_EXTRA

CONF_WOL_TARGET: typing.Final = "wol_target"
CONF_MAX_COUNT = 'maxCount'
CONF_REFRESH_RATE = 'refreshRate'

_LOGGER = logging.getLogger(__name__)
_LOGGER.info('Starting iiyama_sicp')

DEFAULT_VERIFY_SSL = True
MANIFEST = json.load(open("%s/manifest.json" % os.path.dirname(os.path.realpath(__file__))))
VERSION = MANIFEST["version"]
DOMAIN = MANIFEST[CONF_DOMAIN]
DEFAULT_NAME = MANIFEST[CONF_NAME]
PLATFORM = Platform.MEDIA_PLAYER
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
    await hass.config_entries.async_forward_entry_setups(config_entry, [PLATFORM])
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, [PLATFORM])
