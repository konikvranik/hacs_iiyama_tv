from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from functools import partial

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.iiyama_sicp.pyamasicp.client import Client
from custom_components.iiyama_sicp.pyamasicp.commands import INPUT_SOURCES, Commands

_LOGGER = logging.getLogger(__name__)


class SicpData:
    state: bool
    input_source: str
    volume_level: int
    model_id: str
    model: str
    hw_version: str
    sw_version: str


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
            always_update=False,
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

        self.data = SicpData()
        try:
            self.data.model_id = self._api_commands.get_model_number()
            self.data.model = self.data.model_id
            self.data.hw_version = self._api_commands.get_fw_version()
            self.data.sw_version = self._api_commands.get_platform_version()
        except Exception as e:
            raise ConfigEntryNotReady from e

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

            try:
                if self.data is None:
                    self.data = SicpData

                result = SicpData()
                await asyncio.sleep(.5)
                state = self._api_commands.get_power_state()
                result.state = state

                if state:
                    await asyncio.sleep(.5)
                    source_ = self._api_commands.get_input_source()[0]
                    for k, v in INPUT_SOURCES.items():
                        if source_ == v:
                            result.input_source = k
                            self._attr_source = k
                    await asyncio.sleep(.5)

                    result.volume_level = self._api_commands.get_volume()[0] / 100.0

            except Exception as err:
                raise UpdateFailed(f"Error communicating with API: {err}")
            return result

    async def async_set_volume_level(self, volume):
        """Set volume level."""
        await self.hass.async_add_executor_job(partial(self._api_commands.set_volume, output_volume=int(volume * 100)))

    async def async_select_source(self, source):
        """Send source select command."""
        await self.hass.async_add_executor_job(self._api_commands.set_input_source, INPUT_SOURCES[source])

    async def async_turn_off(self):
        """Send turn off command."""
        await self.hass.async_add_executor_job(self._api_commands.set_power_state, False)

    async def async_turn_on(self):
        """Send turn on command."""
        await self.hass.async_add_executor_job(self._api_commands.set_power_state, True)
