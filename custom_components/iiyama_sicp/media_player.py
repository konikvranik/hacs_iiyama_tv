""" mqtt-mediaplayer """
import logging
import uuid
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity, MediaPlayerEntityFeature, \
    MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST, CONF_MAC, )
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

import pyamasicp.commands
from custom_components.iiyama_sicp import CONF_WOL_TARGET, DOMAIN

SCAN_INTERVAL = timedelta(seconds=15)
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
    async_add_entities([(IiyamaSicpMediaPlayer(hass, DeviceInfo(name=config_entry.title,
                                                                identifiers={(DOMAIN, config_entry.entry_id)}),
                                               config_entry.data.get(CONF_NAME), config_entry.data.get(CONF_HOST),
                                               config_entry.data.get(CONF_MAC),
                                               config_entry.data.get(CONF_WOL_TARGET)))], True)


class IiyamaSicpMediaPlayer(MediaPlayerEntity):
    """MQTTMediaPlayer"""

    def __init__(self, hass: HomeAssistant, device_info: DeviceInfo, name: str, host: str, mac: str,
                 wol_target: str) -> None:
        """Initialize"""

        self._attr_device_info = device_info
        _LOGGER.debug("IiyamaSicpMediaPlayer.__init__(%s, %s, %s, %s)" % (name, host, mac, wol_target))
        self.hass = hass
        client = pyamasicp.commands.Client(host, mac=mac, wol_target=wol_target)
        client._logger.setLevel(_LOGGER.getEffectiveLevel())
        _LOGGER.debug(
            'host: %s:%d, mac: %s, wol_target: %s' % (client._host, client._port, client._mac, client._wol_target))
        self._client = pyamasicp.commands.Commands(client)
        self._name = name
        self._host = host
        self._mac = mac
        self._attr_unique_id = mac if mac else str(uuid.uuid4())

        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_SET
        self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOURCE
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_OFF
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_ON
        self._attr_source_list = [b.replace(" ", " ") for b in pyamasicp.commands.INPUT_SOURCES.keys()]
        self._initiated = False
        self._attr_device_info["manufacturer"] = "Iiyama"
        self._attr_device_info["identifiers"].add(("mac", self._mac))
        self._attr_device_info["identifiers"].add(("host", self._host))
        self._attr_device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac), ("host", self._host)}

    def setup_device(self):
        self._attr_device_info["model_id"] = self._client.get_model_number()
        self._attr_device_info["model"] = self._attr_device_info["model_id"]
        self._attr_device_info["hw_version"] = self._client.get_fw_version()
        self._attr_device_info["sw_model"] = self._client.get_platform_label()
        self._attr_device_info["sw_version"] = self._client.get_platform_version()
        self._initiated = True

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
            if not self._initiated:
                try:
                    self.setup_device()
                    _LOGGER.debug("DeviceInfo: %s", self.device_info)
                except Exception:
                    pass

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    def set_volume_level(self, volume):
        """Set volume level."""
        self._client.set_volume(output_volume=int(volume * 100))
        self._attr_volume_level = volume

    def select_source(self, source):
        """Send source select command."""
        self._client.set_input_source(pyamasicp.commands.INPUT_SOURCES[source])
        self._attr_source = source

    def turn_off(self):
        """Send turn off command."""
        self._client.set_power_state(False)
        self._attr_state = MediaPlayerState.OFF

    def turn_on(self):
        """Send turn on command."""
        self._client.set_power_state(True)
        self._attr_state = MediaPlayerState.ON
