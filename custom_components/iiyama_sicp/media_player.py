""" mqtt-mediaplayer """
import logging
import socket
import uuid
from datetime import timedelta
from time import sleep

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import wakeonlan
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

from custom_components.iiyama_sicp import CONF_WOL_TARGET, DOMAIN, CONF_WOL_PORT

REQUIREMENTS="pyamasicp"
#SCAN_INTERVAL = timedelta(minutes=1)
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
                                               config_entry.data.get(CONF_WOL_TARGET),
                                               config_entry.data.get(CONF_WOL_PORT)))], True)


import pyamasicp.commands as pyamasicp


class IiyamaSicpMediaPlayer(MediaPlayerEntity):
    """MQTTMediaPlayer"""

    def __init__(self, hass: HomeAssistant, device_info: DeviceInfo, name: str, host: str, mac: str,
                 broadcast_address: str, broadcast_port: int) -> None:
        """Initialize"""

        self._attr_device_info = device_info
        _LOGGER.debug("IiyamaSicpMediaPlayer.__init__(%s, %s, %s, %s)" % (name, host, mac, broadcast_address))
        self.hass = hass
        self._mac_addresses = mac.split(r'[\s,;]')
        self._broadcast_port = broadcast_port
        self._broadcast_address = broadcast_address
        self._client = pyamasicp.Commands(pyamasicp.Client(host))
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
        self._attr_source_list = [b.replace(" ", " ") for b in pyamasicp.INPUT_SOURCES.keys()]
        self._initiated = False
        self._attr_device_info["manufacturer"] = "Iiyama"
        self._attr_device_info["identifiers"].add(("mac", self._mac))
        self._attr_device_info["identifiers"].add(("host", self._host))
        self._attr_device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac), ("host", self._host)}

    def setup_device(self):
        self._attr_device_info["model_id"] = self._client.get_model_number()
        self._attr_device_info["model"] = self._attr_device_info["model_id"]
        self._attr_device_info["hw_version"] = self._client.get_fw_version()
        self._attr_device_info["sw_version"] = self._client.get_platform_version()
        self._initiated = True

    def update(self):
        """ Update the States"""
        try:
            sleep(.5)
            state = self._client.get_power_state()
            self._attr_state = MediaPlayerState.ON if state else MediaPlayerState.OFF
            if state:
                sleep(.5)
                source_ = self._client.get_input_source()[0]
                for k, v in pyamasicp.INPUT_SOURCES.items():
                    if source_ == v:
                        self._attr_source = k
                sleep(.5)
                self._attr_volume_level = self._client.get_volume()[0] / 100.0
                if not self._initiated:
                    try:
                        sleep(.5)
                        self.setup_device()
                        _LOGGER.debug("DeviceInfo: %s", self.device_info)
                    except Exception:
                        pass
        finally:
            self._client.disconnect()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    def set_volume_level(self, volume):
        """Set volume level."""
        try:
            self._client.set_volume(output_volume=int(volume * 100))
        finally:
            self._client.disconnect()
        self._attr_volume_level = volume

    def select_source(self, source):
        """Send source select command."""
        try:
            self._client.set_input_source(pyamasicp.INPUT_SOURCES[source])
        finally:
            self._client.disconnect()
        self._attr_source = source

    def turn_off(self):
        """Send turn off command."""
        try:
            self._client.set_power_state(False)
        finally:
            self._client.disconnect()
        self._attr_state = MediaPlayerState.OFF

    def turn_on(self):
        """Send turn on command."""

        try:
            self._client.set_power_state(True)
        except socket.error:
            self.wake_on_lan()
        finally:
            self._client.disconnect()
        self._attr_state = MediaPlayerState.ON

    def wake_on_lan(self):
        service_kwargs = {}
        if self._broadcast_address is not None:
            service_kwargs["ip_address"] = self._broadcast_address
        if self._broadcast_port is not None:
            service_kwargs["port"] = self._broadcast_port

        _LOGGER.debug(
            "Send magic packet to mac %s (broadcast: %s, port: %s)",
            self._mac_addresses,
            self._broadcast_address,
            self._broadcast_port,
        )
        wakeonlan.send_magic_packet(*self._mac_addresses, **service_kwargs)
