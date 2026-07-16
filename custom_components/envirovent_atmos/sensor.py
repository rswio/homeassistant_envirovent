"""Sensors: filter days, hours run, airflow %, mode, and setpoints (diagnostic)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .atmos import AtmosState
from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity


def _airflow_percent(s: AtmosState) -> StateType:
    if s.airflow_is_variable:
        return s.variable_percent
    return s.percent_for_speed(s.preset_speed)


@dataclass(frozen=True, kw_only=True)
class AtmosSensorDescription(SensorEntityDescription):
    """Describes an ATMOS sensor."""

    value_fn: Callable[[AtmosState], StateType]


SENSORS: tuple[AtmosSensorDescription, ...] = (
    AtmosSensorDescription(
        key="filter_days_remaining",
        translation_key="filter_days_remaining",
        icon="mdi:air-filter",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filter_remaining_days,
    ),
    AtmosSensorDescription(
        key="hours_run",
        translation_key="hours_run",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.hours_run,
    ),
    AtmosSensorDescription(
        key="airflow_percent",
        translation_key="airflow_percent",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_airflow_percent,
    ),
    AtmosSensorDescription(
        key="airflow_mode",
        translation_key="airflow_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["preset", "variable"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: "variable" if s.airflow_is_variable else "preset",
    ),
    AtmosSensorDescription(
        key="heater_setpoint",
        translation_key="heater_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.heater_temperature,
    ),
    AtmosSensorDescription(
        key="summer_setpoint",
        translation_key="summer_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.summer_temperature,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(AtmosSensor(entry.runtime_data, desc) for desc in SENSORS)


class AtmosSensor(EnviroventAtmosEntity, SensorEntity):
    """A read-only value from the unit."""

    entity_description: AtmosSensorDescription

    def __init__(self, coordinator, description: AtmosSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        state = self.coordinator.data
        if state is None:
            return None
        return self.entity_description.value_fn(state)
