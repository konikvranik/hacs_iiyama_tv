from __future__ import annotations

import async_timeout
import asyncio
import getmac
import logging
import socket
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_HOST
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.iiyama_sicp.pyamasicp.client import Client
from custom_components.iiyama_sicp.pyamasicp.commands import INPUT_SOURCES, Commands

_LOGGER = logging.getLogger(__name__)


@dataclass
class SicpData:
    state: bool = None
    input_source: str = None
    volume_level: int = None
    model_id: str = None
    model: str = None
    hw_version: str = None
    sw_version: str = None


class SicpUpdateCoordinator(DataUpdateCoordinator[SicpData]):
    """HKO Update Coordinator."""

    def __init__(self, hass, config_entry: ConfigEntry, client: Client):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="iiyama SICP",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,
            config_entry=config_entry
        )
        self._api_client = client
        self._api_commands = Commands(client)

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """

        await self._setup_mac()

        try:
            await self._setup_device_info()
        except Exception as err:
            self._api_client.close()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with async_timeout.timeout(10):
            # Grab active context variables to limit data required to be fetched from API
            # Note: using context is not required if there is no need or ability to limit
            # data retrieved from API.

            listening_idx = set(self.async_contexts())
            _LOGGER.debug("Listening contexts: %s", listening_idx)

        await self._setup_mac()

        if self.data is None:
            self.data = SicpData()
        result = self.data

        try:
            await self._setup_device_info()

            # await asyncio.sleep(.5)
            try:
                result.state = self._api_commands.get_power_state()
                _LOGGER.debug(f"Got state: {result.state}")
            except socket.error as e:
                result.state = False
                _LOGGER.debug(f"Failed to get state: {e}")
                self._api_client.close()
                return result

            # await asyncio.sleep(.5)
            source_ = self._api_commands.get_input_source()[0]
            for k, v in INPUT_SOURCES.items():
                if source_ == v:
                    result.input_source = k
            # await asyncio.sleep(.5)

            result.volume_level = self._api_commands.get_volume()[0] / 100.0

        except socket.error as e:
            result.state = False
            self._api_client.close()
            return result
        except Exception as err:
            self._api_client.close()
            raise UpdateFailed(f"Error communicating with API: {err}")
        return result

    async def _setup_device_info(self):
        if not self.data:
            self.data = SicpData()
        if not self.data.model_id:
            self.data.model_id = self._api_commands.get_model_number()
        if (not self.data.model) and self.data.model_id:
            self.data.model = self.data.model_id
        if not self.data.hw_version:
            self.data.hw_version = self._api_commands.get_fw_version()
        if not self.data.sw_version:
            self.data.sw_version = self._api_commands.get_platform_version()

    async def _setup_mac(self):
        try:
            data = {**self.config_entry.data}
            if not (CONF_MAC in data and data[CONF_MAC]):
                data[CONF_MAC] = getmac.get_mac_address(ip=data[CONF_HOST], hostname=data[CONF_HOST])
                self.hass.config_entries.async_update_entry(self.config_entry, data=data, minor_version=1, version=1)
        except Exception as e:
            self.logger.warning("Failed to get MAC address", exc_info=e)

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self._api_client.close)

    async def async_set_volume_level(self, volume):
        """Set volume level."""
        await self.hass.async_add_executor_job(partial(self._api_commands.set_volume, volume=int(volume * 100)))

    async def async_select_source(self, source):
        """Send source select command."""
        await self.hass.async_add_executor_job(self._api_commands.set_input_source, INPUT_SOURCES[source])

    async def async_turn_off(self):
        """Send turn off command."""
        await self.hass.async_add_executor_job(self._api_commands.set_power_state, False)

    async def async_turn_on(self):
        """Send turn on command."""
        await self.hass.async_add_executor_job(self._api_commands.set_power_state, True)
