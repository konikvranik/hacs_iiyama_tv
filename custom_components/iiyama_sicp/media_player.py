""" mqtt-mediaplayer """
import logging

import homeassistant.helpers.config_validation as cv
import pyamasicp.commands
import voluptuous as vol
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity, MediaPlayerEntityFeature, \
    MediaType, MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST, CONF_MAC,
)
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
    sensor = IiyamaSicpMediaPlayer(hass, config_entry.get(CONF_NAME), config_entry.get(CONF_HOST),
                                   config_entry.get(CONF_MAC), config_entry.get(CONF_WOL_TARGET))
    async_add_entities([sensor], True)


class IiyamaSicpMediaPlayer(MediaPlayerEntity):
    """MQTTMediaPlayer"""

    def __init__(self, hass: HomeAssistant, name: str, host: str, mac: str, wol_target: str) -> None:
        """Initialize"""

        _LOGGER.warning("IiyamaSicpMediaPlayer.__init__(%s, %s, %s, %s)" % (name, host, mac, wol_target))

        self.hass = hass
        client = pyamasicp.commands.Client(host, mac=mac, wol_target=wol_target)
        client._logger.setLevel(_LOGGER.getEffectiveLevel())
        self._client = pyamasicp.commands.Commands(client)
        self._domain = __name__.split(".")[-2]
        self._name = name
        self._volume = 0.0
        self._mqtt_player_state = None
        self._state = None
        self._album_art = None
        self._vol_down_action = None
        self._vol_up_action = None
        self._vol_script = None
        self._select_source_script = None
        self._turn_off_script = None
        self._turn_on_script = None
        self._source = None

        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_SET
        self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOURCE
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_OFF
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_ON

    async def async_setup(self):
        """Set up the MQTT subscriptions."""
        self.update()

    @property
    def source_list(self):
        return pyamasicp.commands.INPUT_SOURCES.keys()

    def update(self):
        """ Update the States"""
        self._source = self._client.get_input_source()[0]
        self._volume = self._client.get_volume()[0]
        self._state = self._client.get_power_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume / 100.0

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MediaType.VIDEO

    async def async_volume_up(self):
        """Volume up the media player."""
        newvolume = min(self._volume + 5, 100)
        self._volume = newvolume
        await self.async_set_volume_level(newvolume)

    async def async_volume_down(self):
        """Volume down media player."""
        newvolume = max(self._volume - 5, 0)
        self._volume = newvolume
        await self.async_set_volume_level(newvolume)

    async def async_set_volume_level(self, volume):
        """Set volume level."""
        await self.hass.async_add_executor_job(self._client.set_volume, volume * 100)
        self._volume = volume

    async def async_select_source(self, source):
        """Send source select command."""
        self._source = pyamasicp.commands.INPUT_SOURCES[source]
        await self.hass.async_add_executor_job(self._client.set_input_source, self._source)

    async def async_turn_off(self):
        """Send turn off command."""
        await self.hass.async_add_executor_job(self._client.set_power_state, False)

    async def async_turn_on(self):
        """Send turn on command."""
        await self.hass.async_add_executor_job(self._client.set_power_state, True)

    @property
    def source(self):
        for k, v in pyamasicp.commands.INPUT_SOURCES.items():
            if v == self._source:
                return k
