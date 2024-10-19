""" mqtt-mediaplayer """
import logging

import homeassistant.helpers.config_validation as cv
import pyamasicp.commands
import voluptuous as vol
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity, MediaPlayerEntityFeature, \
    MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST, CONF_MAC, )
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.iiyama_sicp import CONF_WOL_TARGET

_LOGGER = logging.getLogger(__name__)
_VALID_STATES = [
    MediaPlayerState.ON,
    MediaPlayerState.OFF,
    "true",
    "false",
]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_MAC): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Set up ESPHome binary sensors based on a config entry."""
    config_entry = config_entry.data
    async_add_entities([(IiyamaSicpMediaPlayer(hass, config_entry.get(CONF_NAME), config_entry.get(CONF_HOST),
                                               config_entry.get(CONF_MAC), config_entry.get(CONF_WOL_TARGET)))], True)


class IiyamaSicpMediaPlayer(MediaPlayerEntity):
    """MQTTMediaPlayer"""

    def __init__(self, hass: HomeAssistant, name: str, host: str, mac: str, wol_target: str) -> None:
        """Initialize"""

        _LOGGER.debug("IiyamaSicpMediaPlayer.__init__(%s, %s, %s, %s)" % (name, host, mac, wol_target))
        self.hass = hass
        client = pyamasicp.commands.Client(host, mac=mac, wol_target=wol_target)
        client._logger.setLevel(_LOGGER.getEffectiveLevel())
        _LOGGER.debug(
            'host: %s:%d, mac: %s, wol_target: %s' % (client._host, client._port, client._mac, client._wol_target))
        self._client = pyamasicp.commands.Commands(client)
        self._name = name

        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_SET
        self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOURCE
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_OFF
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_ON

        self._attr_source_list = [b.replace(" ", " ") for b in pyamasicp.commands.INPUT_SOURCES.keys()]

    def update(self):
        """ Update the States"""
        state = self._client.get_power_state()
        self._attr_state = MediaPlayerState.ON if state else MediaPlayerState.OFF
        if state:
            source_ = self._client.get_input_source()[0]
            for k, v in pyamasicp.commands.INPUT_SOURCES.items():
                if source_ == v:
                    self._attr_source = k
            self._attr_volume_level = self._client.get_volume()[0] / 100.0

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    def set_volume_level(self, volume):
        """Set volume level."""
        self._attr_volume_level = volume
        self._client.set_volume(output_volume=int(self._attr_volume_level * 100))

    def select_source(self, source):
        """Send source select command."""
        self._attr_source = source
        self._client.set_input_source(pyamasicp.commands.INPUT_SOURCES[self._attr_source])

    def turn_off(self):
        """Send turn off command."""
        self._attr_state = MediaPlayerState.OFF
        self._client.set_power_state(False)

    def turn_on(self):
        """Send turn on command."""
        self._attr_state = MediaPlayerState.ON
        self._client.set_power_state(True)
