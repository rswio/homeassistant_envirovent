"""Config flow for EnviroVent ATMOS."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .atmos import AtmosClient, AtmosError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def _probe(host: str, port: int):
    """Return the decoded state, raising AtmosError on failure."""
    return await AtmosClient(host, port, timeout=8.0, retries=1).async_get_state()


class EnviroventAtmosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnviroVent ATMOS."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            try:
                state = await _probe(host, port)
            except AtmosError:
                errors["base"] = "cannot_connect"
            else:
                if (state.unit_type or "").upper() != "PIV":
                    errors["base"] = "not_piv"
                else:
                    await self.async_set_unique_id(f"{host}:{port}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"EnviroVent ATMOS ({host})",
                        data={CONF_HOST: host, CONF_PORT: port},
                    )

        suggested = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=suggested.get(CONF_HOST, DEFAULT_HOST)
                ): str,
                vol.Optional(
                    CONF_PORT, default=suggested.get(CONF_PORT, DEFAULT_PORT)
                ): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a discovered unit. The control port is fixed 1337, NOT the
        _http._tcp SRV port the unit advertises (the app ignores that port too)."""
        host = discovery_info.host
        port = DEFAULT_PORT
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        try:
            state = await _probe(host, port)
        except AtmosError:
            return self.async_abort(reason="cannot_connect")
        if (state.unit_type or "").upper() != "PIV":
            return self.async_abort(reason="not_piv")

        self._host = host
        self._port = port
        self.context["title_placeholders"] = {"name": f"ATMOS ({host})"}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._host is not None
        if user_input is not None:
            return self.async_create_entry(
                title=f"EnviroVent ATMOS ({self._host})",
                data={CONF_HOST: self._host, CONF_PORT: self._port},
            )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._host},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return EnviroventAtmosOptionsFlow()


class EnviroventAtmosOptionsFlow(OptionsFlow):
    """Options: poll interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
