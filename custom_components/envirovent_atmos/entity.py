"""Base entity for the EnviroVent ATMOS integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EnviroventAtmosCoordinator


class EnviroventAtmosEntity(CoordinatorEntity[EnviroventAtmosCoordinator]):
    """Common base: device grouping + availability from the shared coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnviroventAtmosCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        state = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
            sw_version=state.software_version if state else None,
            configuration_url=None,
        )

    @property
    def available(self) -> bool:
        """Unavailable if the coordinator failed or the unit reported an error."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.success
        )

    async def _async_run(self, coro) -> None:
        """Await a client command then refresh shared state."""
        await coro
        await self.coordinator.async_request_refresh()
