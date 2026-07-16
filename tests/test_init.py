"""Setup + entity/command tests using a mocked client (no device needed)."""
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.envirovent_atmos.atmos import AtmosState
from custom_components.envirovent_atmos.const import DOMAIN

from .conftest import SAMPLE_RESPONSE

CLIENT = "custom_components.envirovent_atmos.atmos.client.AtmosClient"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.0.5", CONF_PORT: 1337},
        title="EnviroVent ATMOS",
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        f"{CLIENT}.async_get_state",
        new=AsyncMock(return_value=AtmosState.from_response(SAMPLE_RESPONSE)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_setup_creates_entities(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    fan = hass.states.get("fan.envirovent_atmos")
    assert fan is not None and fan.state == "on"
    assert fan.attributes["percentage"] == 74
    assert fan.attributes["preset_mode"] == "Speed 4"
    assert fan.attributes["preset_modes"] == ["Speed 1", "Speed 2", "Speed 3", "Speed 4"]

    assert hass.states.get("switch.envirovent_atmos_boost").state == "off"
    assert hass.states.get("switch.envirovent_atmos_auto_heater").state == "on"
    assert hass.states.get("sensor.envirovent_atmos_filter_days_remaining").state == "1813"
    assert hass.states.get("sensor.envirovent_atmos_hours_run").state == "6346"
    assert hass.states.get("select.envirovent_atmos_filter_period").state == "60"
    assert (
        hass.states.get("binary_sensor.envirovent_atmos_filter_needs_changing").state
        == "off"
    )


async def test_boost_switch_calls_client(hass: HomeAssistant) -> None:
    await _setup(hass)
    with (
        patch(f"{CLIENT}.async_set_boost", new=AsyncMock()) as set_boost,
        patch(
            f"{CLIENT}.async_get_state",
            new=AsyncMock(return_value=AtmosState.from_response(SAMPLE_RESPONSE)),
        ),
    ):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.envirovent_atmos_boost"},
            blocking=True,
        )
    set_boost.assert_awaited_once_with(True)


async def test_fan_set_preset_calls_client(hass: HomeAssistant) -> None:
    await _setup(hass)
    with (
        patch(f"{CLIENT}.async_set_preset_speed", new=AsyncMock()) as set_speed,
        patch(
            f"{CLIENT}.async_get_state",
            new=AsyncMock(return_value=AtmosState.from_response(SAMPLE_RESPONSE)),
        ),
    ):
        await hass.services.async_call(
            "fan",
            "set_preset_mode",
            {"entity_id": "fan.envirovent_atmos", "preset_mode": "Speed 2"},
            blocking=True,
        )
    assert set_speed.await_args.args[0] == 2
