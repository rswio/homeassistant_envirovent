"""Select entities: boost duration and filter period (discrete options)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .atmos import AtmosClient, AtmosState
from .atmos.const import BOOST_MINUTES_OPTIONS, FILTER_MONTHS_OPTIONS
from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity


@dataclass(frozen=True, kw_only=True)
class AtmosSelectDescription(SelectEntityDescription):
    """Describes an ATMOS select."""

    values: tuple[int, ...]
    current_fn: Callable[[AtmosState], int]
    set_fn: Callable[[AtmosClient, int, AtmosState], Awaitable[None]]


SELECTS: tuple[AtmosSelectDescription, ...] = (
    AtmosSelectDescription(
        key="boost_duration",
        translation_key="boost_duration",
        icon="mdi:timer-cog",
        entity_category=EntityCategory.CONFIG,
        values=BOOST_MINUTES_OPTIONS,
        current_fn=lambda s: s.boost_minutes,
        set_fn=lambda c, v, s: c.async_set_boost_duration(v, state=s),
    ),
    AtmosSelectDescription(
        key="filter_period",
        translation_key="filter_period",
        icon="mdi:air-filter",
        entity_category=EntityCategory.CONFIG,
        values=FILTER_MONTHS_OPTIONS,
        current_fn=lambda s: s.filter_reset_months,
        set_fn=lambda c, v, s: c.async_set_filter_period(v, state=s),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(AtmosSelect(entry.runtime_data, desc) for desc in SELECTS)


class AtmosSelect(EnviroventAtmosEntity, SelectEntity):
    """A discrete-option resident setting."""

    entity_description: AtmosSelectDescription

    def __init__(self, coordinator, description: AtmosSelectDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_options = [str(v) for v in description.values]

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.data
        if state is None:
            return None
        return str(self.entity_description.current_fn(state))

    async def async_select_option(self, option: str) -> None:
        await self._async_run(
            self.entity_description.set_fn(
                self.coordinator.client, int(option), self.coordinator.data
            )
        )
