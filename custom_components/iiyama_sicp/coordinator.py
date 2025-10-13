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

from pyamasicp.client import Client
from pyamasicp.commands import INPUT_SOURCES, Commands

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
            await self.hass.async_add_executor_job(self._api_client.close)

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

            # Parallelize state, source, and volume reads to bound total latency
            state_fut = self.hass.async_add_executor_job(self._api_commands.get_power_state)
            source_fut = self.hass.async_add_executor_job(self._api_commands.get_input_source)
            volume_fut = self.hass.async_add_executor_job(self._api_commands.get_volume)
            try:
                result_state, source_bytes, volume_bytes = await asyncio.gather(state_fut, source_fut, volume_fut)
                result.state = result_state
                _LOGGER.debug(f"Got state: {result.state}")
                source_ = source_bytes[0] if source_bytes else None
                for k, v in INPUT_SOURCES.items():
                    if source_ == v:
                        result.input_source = k
                result.volume_level = (volume_bytes[0] / 100.0) if volume_bytes else None
            except socket.error as e:
                _LOGGER.debug(f"Failed to read device status: {e}")
                raise e

        except socket.error as e:
            await self.hass.async_add_executor_job(self._api_client.close)
            _LOGGER.error(f"Socket error during update of the device status: {e}")
            raise UpdateFailed(f"Socket error: {e}")
        except Exception as err:
            await self.hass.async_add_executor_job(self._api_client.close)
            _LOGGER.error(f"Failed to update the device status: {err}")
            raise UpdateFailed(f"Error communicating with API: {err}")
        return result

    async def _setup_device_info(self):
        if not self.data:
            self.data = SicpData()
        if not self.data.model_id:
            try:
                self.data.model_id = await self.hass.async_add_executor_job(self._api_commands.get_model_number)
            except Exception as e:
                _LOGGER.debug(f"Failed to get model ID: {e}")
                self.data.model_id = "Unknown"
        if (not self.data.model) and self.data.model_id:
            try:
                self.data.model = self.data.model_id
            except Exception as e:
                _LOGGER.debug(f"Failed to get model name: {e}")
                self.data.model = "Unknown"
        if not self.data.hw_version:
            try:
                self.data.hw_version = await self.hass.async_add_executor_job(self._api_commands.get_fw_version)
            except Exception as e:
                _LOGGER.debug(f"Failed to get hardware version: {e}")
                self.data.hw_version = "Unknown"
        if not self.data.sw_version:
            try:
                self.data.sw_version = await self.hass.async_add_executor_job(self._api_commands.get_platform_version)
            except Exception as e:
                _LOGGER.debug(f"Failed to get software version: {e}")
                self.data.sw_version = "Unknown"

    async def _setup_mac(self):
        try:
            data = {**self.config_entry.data}
            if not (CONF_MAC in data and data[CONF_MAC]):
                mac = await self.hass.async_add_executor_job(
                    partial(getmac.get_mac_address, ip=data[CONF_HOST], hostname=data[CONF_HOST])
                )
                data[CONF_MAC] = mac
                self.hass.config_entries.async_update_entry(self.config_entry, data=data, minor_version=1, version=1)
        except Exception as e:
            _LOGGER.warning("Failed to get MAC address", exc_info=e)

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
