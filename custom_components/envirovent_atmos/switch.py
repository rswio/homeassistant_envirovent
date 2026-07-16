"""Switch entities: boost, auto heater enable, summer mode enable."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .atmos import AtmosClient, AtmosState
from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity


@dataclass(frozen=True, kw_only=True)
class AtmosSwitchDescription(SwitchEntityDescription):
    """Describes an ATMOS switch."""

    value_fn: Callable[[AtmosState], bool]
    set_fn: Callable[[AtmosClient, bool, AtmosState], Awaitable[None]]


SWITCHES: tuple[AtmosSwitchDescription, ...] = (
    AtmosSwitchDescription(
        key="boost",
        translation_key="boost",
        icon="mdi:fan-plus",
        value_fn=lambda s: s.boost_on,
        set_fn=lambda c, on, s: c.async_set_boost(on),
    ),
    AtmosSwitchDescription(
        key="auto_heater",
        translation_key="auto_heater",
        icon="mdi:radiator",
        value_fn=lambda s: s.auto_heater_on,
        set_fn=lambda c, on, s: c.async_set_auto_heater(on, state=s),
    ),
    AtmosSwitchDescription(
        key="summer_mode",
        translation_key="summer_mode",
        icon="mdi:weather-sunny",
        value_fn=lambda s: s.summer_mode_enabled,
        set_fn=lambda c, on, s: c.async_set_summer_mode(on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(AtmosSwitch(entry.runtime_data, desc) for desc in SWITCHES)


class AtmosSwitch(EnviroventAtmosEntity, SwitchEntity):
    """A resident-safe on/off control."""

    entity_description: AtmosSwitchDescription

    def __init__(self, coordinator, description: AtmosSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data
        if state is None:
            return None
        return self.entity_description.value_fn(state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_run(
            self.entity_description.set_fn(
                self.coordinator.client, True, self.coordinator.data
            )
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_run(
            self.entity_description.set_fn(
                self.coordinator.client, False, self.coordinator.data
            )
        )
