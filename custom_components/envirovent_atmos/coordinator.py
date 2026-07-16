"""DataUpdateCoordinator for the EnviroVent ATMOS unit."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .atmos import AtmosClient, AtmosError, AtmosState
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EnviroventAtmosCoordinator(DataUpdateCoordinator[AtmosState]):
    """Polls the unit once and shares the result with all entities.

    The unit accepts only one TCP client at a time, so a single shared poll
    (instead of per-entity requests) keeps traffic minimal.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AtmosClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> AtmosState:
        try:
            return await self.client.async_get_state()
        except AtmosError as err:
            raise UpdateFailed(f"Error communicating with ATMOS unit: {err}") from err


type EnviroventConfigEntry = ConfigEntry[EnviroventAtmosCoordinator]
