"""Button entity: reset the filter-change counter."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AtmosResetFilterButton(entry.runtime_data)])


class AtmosResetFilterButton(EnviroventAtmosEntity, ButtonEntity):
    """Resets the filter maintenance countdown (FilterMaintenanceComplete)."""

    _attr_translation_key = "reset_filter"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "reset_filter")

    async def async_press(self) -> None:
        await self._async_run(self.coordinator.client.async_reset_filter())
