""" mqtt-mediaplayer """
import inspect
import logging
import socket
import uuid
import re

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import wakeonlan
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity, MediaPlayerEntityFeature, \
    MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST, CONF_MAC, )
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.iiyama_sicp import CONF_WOL_TARGET, DOMAIN, CONF_WOL_PORT, SicpUpdateCoordinator
from custom_components.iiyama_sicp.pyamasicp.client import Client
from custom_components.iiyama_sicp.pyamasicp.commands import INPUT_SOURCES, Commands

# SCAN_INTERVAL = timedelta(minutes=1)
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
                                               config_entry.runtime_data['coordinator'],
                                               config_entry.data.get(CONF_NAME), config_entry.data.get(CONF_HOST),
                                               config_entry.data.get(CONF_MAC),
                                               config_entry.data.get(CONF_WOL_TARGET),
                                               config_entry.data.get(CONF_WOL_PORT)))], True)


class IiyamaSicpMediaPlayer(CoordinatorEntity[SicpUpdateCoordinator], MediaPlayerEntity):
    """MQTTMediaPlayer"""

    def __init__(self, hass: HomeAssistant, device_info: DeviceInfo, coordinator: SicpUpdateCoordinator, name: str,
                 host: str, mac: str,
                 broadcast_address: str, broadcast_port: int) -> None:
        """Initialize"""

        super().__init__(coordinator)
        self._attr_device_info = device_info
        _LOGGER.debug("IiyamaSicpMediaPlayer.__init__(%s, %s, %s, %s)" % (name, host, mac, broadcast_address))
        self.hass = hass
        self._mac_addresses = re.split(r"[\s,;]+", mac) if mac else []
        self._broadcast_port = broadcast_port
        self._broadcast_address = broadcast_address
        # Removed unused per-entity client; all operations go through the coordinator
        self._attr_name = name
        self._attr_unique_id = f"iiyama_sicp_{host}_{mac}"
        self._host = host
        self._mac = mac

        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_SET
        self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOURCE
        self._attr_supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_OFF
        self._attr_supported_features |= MediaPlayerEntityFeature.TURN_ON
        self._attr_source_list = [b.replace(" ", " ") for b in INPUT_SOURCES.keys()]
        self._initiated = False
        self._attr_device_info["manufacturer"] = "Iiyama"
        self._attr_device_info["identifiers"].add(("mac", self._mac))
        self._attr_device_info["identifiers"].add(("host", self._host))
        self._attr_device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac), ("host", self._host)}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_state = MediaPlayerState.ON if hasattr(self.coordinator.data,
                                                          'state') and self.coordinator.data.state else MediaPlayerState.OFF

        _LOGGER.debug(f"State updated to: {self._attr_state} from {inspect.getmembers(self.coordinator.data)}")
        self._attr_source = self.coordinator.data.input_source
        self._attr_volume_level = self.coordinator.data.volume_level

        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        await self.coordinator.async_set_volume_level(volume)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source):
        """Send source select command."""
        await self.coordinator.async_select_source(source)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        """Send turn off command."""
        await self.coordinator.async_turn_off()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self):
        """Send turn on command."""

        try:
            await self.coordinator.async_turn_on()
        except socket.error:
            self.wake_on_lan()
        await self.coordinator.async_request_refresh()

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
