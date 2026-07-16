"""Fan entity for the ATMOS airflow (4 fixed presets + variable percentage)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EnviroventConfigEntry
from .entity import EnviroventAtmosEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnviroventConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EnviroventAtmosFan(entry.runtime_data)])


def _speed_num(preset_mode: str) -> int:
    return int(preset_mode.rsplit(" ", 1)[-1])


class EnviroventAtmosFan(EnviroventAtmosEntity, FanEntity):
    """The unit's airflow. Preset modes = fixed speeds (SET); percentage = variable (VAR).

    The PIV runs continuously, so the fan is modelled as always-on; turning it
    'off' is not supported by the unit's protocol.
    """

    _attr_name = None  # primary entity -> takes the device name
    _attr_translation_key = "airflow"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fan")

    @property
    def is_on(self) -> bool:
        return self.available

    @property
    def preset_modes(self) -> list[str]:
        state = self.coordinator.data
        count = state.max_preset if state and state.max_preset else 4
        return [f"Speed {i}" for i in range(1, count + 1)]

    @property
    def preset_mode(self) -> str | None:
        state = self.coordinator.data
        if state is None or state.airflow_is_variable or state.preset_speed is None:
            return None
        return f"Speed {state.preset_speed}"

    @property
    def percentage(self) -> int | None:
        state = self.coordinator.data
        if state is None:
            return None
        if state.airflow_is_variable:
            return state.variable_percent
        return state.percent_for_speed(state.preset_speed) or 0

    @property
    def percentage_step(self) -> float:
        return 1.0

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._async_run(
            self.coordinator.client.async_set_preset_speed(
                _speed_num(preset_mode), state=self.coordinator.data
            )
        )

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage <= 0:
            _LOGGER.debug("ATMOS PIV cannot be turned off; ignoring percentage 0")
            return
        await self._async_run(
            self.coordinator.client.async_set_variable_airflow(
                percentage, state=self.coordinator.data
            )
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        # otherwise the unit is already running — nothing to do

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.warning(
            "The EnviroVent ATMOS PIV ventilates continuously and cannot be "
            "turned off via the local protocol; ignoring turn_off"
        )
