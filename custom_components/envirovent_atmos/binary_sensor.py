"""Binary sensors: active-state read-outs from the unit."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .atmos import AtmosState
from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity


@dataclass(frozen=True, kw_only=True)
class AtmosBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an ATMOS binary sensor."""

    value_fn: Callable[[AtmosState], bool]


BINARY_SENSORS: tuple[AtmosBinarySensorDescription, ...] = (
    AtmosBinarySensorDescription(
        key="airflow_active",
        translation_key="airflow_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.airflow_active,
    ),
    AtmosBinarySensorDescription(
        key="boost_input",
        translation_key="boost_input",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.boost_input_on,
    ),
    AtmosBinarySensorDescription(
        key="summer_bypass_active",
        translation_key="summer_bypass_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.summer_active,
    ),
    AtmosBinarySensorDescription(
        key="kick_up",
        translation_key="kick_up",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.kick_up_active,
    ),
    AtmosBinarySensorDescription(
        key="filter_needs_changing",
        translation_key="filter_needs_changing",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: s.filter_needs_changing,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        AtmosBinarySensor(entry.runtime_data, desc) for desc in BINARY_SENSORS
    )


class AtmosBinarySensor(EnviroventAtmosEntity, BinarySensorEntity):
    """A read-only active-state flag."""

    entity_description: AtmosBinarySensorDescription

    def __init__(self, coordinator, description: AtmosBinarySensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data
        if state is None:
            return None
        return self.entity_description.value_fn(state)
