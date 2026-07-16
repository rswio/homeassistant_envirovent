"""Async client for the EnviroVent ATMOS PIV local JSON-over-TCP protocol.

Dependency-free (stdlib asyncio + json). One request per connection; requests are
serialized through a lock because the unit accepts only one TCP client at a time.
Installer/commissioning writes are gated behind ``allow_installer`` (default off).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from .const import (
    AIRFLOW_MODE_SET,
    AIRFLOW_MODE_VAR,
    BOOST_MINUTES_OPTIONS,
    CMD_FILTER_MAINTENANCE_COMPLETE,
    CMD_GET_CURRENT_SETTINGS,
    CMD_RESTORE_COMMISSIONING_DEFAULTS,
    CMD_RESTORE_HOME_DEFAULTS,
    CMD_RESTORE_INSTALLER_DEFAULTS,
    CMD_SET_BOOST,
    CMD_SET_HOME_SETTINGS,
    CMD_SET_INSTALLER_SETTINGS,
    CMD_SET_SPIGOT_TYPE,
    CMD_SET_SUMMER_BYPASS,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    FILTER_MONTHS_OPTIONS,
    HEATER_TEMP_MAX,
    HEATER_TEMP_MIN,
    SUMMER_TEMP_MAX,
    SUMMER_TEMP_MIN,
)
from .models import AtmosState

_LOGGER = logging.getLogger(__name__)


class AtmosError(Exception):
    """Base error."""


class AtmosConnectionError(AtmosError):
    """Could not reach the unit (connection refused / timeout / busy)."""


class AtmosResponseError(AtmosError):
    """The unit replied but the reply was invalid or reported no success."""


class AtmosCommandError(AtmosError):
    """A write command returned success != 1."""


class AtmosInstallerLockedError(AtmosError):
    """An installer/commissioning write was attempted without allow_installer=True."""


class AtmosClient:
    """Talks to one ATMOS PIV unit over TCP/1337."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        allow_installer: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self._timeout = timeout
        self._retries = retries
        self._retry_delay = retry_delay
        self._allow_installer = allow_installer
        self._lock = asyncio.Lock()

    # ---------------- low-level transport ----------------

    async def _exchange(self, body: bytes) -> str:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            writer.write(body)
            await writer.drain()
            buf = b""
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buf += chunk
                try:
                    json.loads(buf.decode("utf-8", "replace"))
                    break  # complete JSON received
                except json.JSONDecodeError:
                    continue
            return buf.decode("utf-8", "replace")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # pragma: no cover - best effort close
                pass

    async def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        async with self._lock:  # serialize: unit is single-client
            last_exc: Optional[BaseException] = None
            for attempt in range(self._retries + 1):
                try:
                    raw = await asyncio.wait_for(self._exchange(body), self._timeout)
                except (OSError, asyncio.TimeoutError) as exc:
                    last_exc = exc
                    _LOGGER.debug(
                        "ATMOS %s:%s attempt %d/%d failed: %r",
                        self.host, self.port, attempt + 1, self._retries + 1, exc,
                    )
                    if attempt < self._retries:
                        await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue
                if not raw:
                    last_exc = AtmosConnectionError("empty response")
                    if attempt < self._retries:
                        await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue
                obj = self._parse_json(raw)
                if obj is None:
                    raise AtmosResponseError(
                        f"invalid JSON from {self.host}:{self.port}; raw={raw[:200]!r}"
                    )
                return obj
            raise AtmosConnectionError(
                f"no response from {self.host}:{self.port} after {self._retries + 1} attempts"
            ) from last_exc

    @staticmethod
    def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
        """Parse the reply, tolerating trailing bytes after the JSON object."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            end = raw.rfind("}")
            if end != -1:
                try:
                    return json.loads(raw[: end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    @staticmethod
    def _check(obj: Dict[str, Any], name: str) -> Dict[str, Any]:
        try:
            ok = int(obj.get("success", 0)) == 1
        except (TypeError, ValueError):
            ok = False
        if not ok:
            raise AtmosCommandError(f"{name} failed: error={obj.get('error')!r} raw={obj}")
        return obj

    # ---------------- reads ----------------

    async def async_get_state(self) -> AtmosState:
        """Fetch and decode the full unit state (GetCurrentSettings)."""
        obj = await self._request({"command": CMD_GET_CURRENT_SETTINGS})
        try:
            ok = int(obj.get("success", 0)) == 1
        except (TypeError, ValueError):
            ok = False
        if not ok:
            raise AtmosResponseError(f"GetCurrentSettings returned failure: {obj}")
        return AtmosState.from_response(obj)

    async def async_get_raw(self) -> Dict[str, Any]:
        """Raw GetCurrentSettings dict (for debugging/probe)."""
        return await self._request({"command": CMD_GET_CURRENT_SETTINGS})

    # ---------------- resident-safe writes ----------------

    async def async_set_boost(self, on: bool) -> None:
        """Turn boost mode on/off (the most reversible write)."""
        self._check(await self._request({"command": CMD_SET_BOOST, "enabled": 1 if on else 0}), "SetBoost")

    async def async_set_summer_mode(self, on: bool) -> None:
        """Turn summer mode (summer bypass shutdown) on/off."""
        self._check(
            await self._request({"command": CMD_SET_SUMMER_BYPASS, "enabled": 1 if on else 0}),
            "SetSummerBypass",
        )

    async def async_reset_filter(self) -> None:
        """Reset the filter-change countdown."""
        self._check(await self._request({"command": CMD_FILTER_MAINTENANCE_COMPLETE}), "FilterMaintenanceComplete")

    async def async_set_preset_speed(self, speed: int, *, state: Optional[AtmosState] = None) -> None:
        """Select a fixed preset airflow speed (1..max_preset)."""
        st = state or await self.async_get_state()
        if st.max_preset and not (1 <= int(speed) <= st.max_preset):
            raise ValueError(f"preset speed {speed} out of range 1..{st.max_preset}")
        await self._apply_home_settings(st, airflow_mode=AIRFLOW_MODE_SET, airflow_value=int(speed))

    async def async_set_variable_airflow(self, percent: int, *, state: Optional[AtmosState] = None) -> None:
        """Set variable airflow to a percentage (within the unit's min..max)."""
        st = state or await self.async_get_state()
        lo = st.variable_min_percent or 0
        hi = st.variable_max_percent or 100
        pct = max(lo, min(hi, int(percent)))
        await self._apply_home_settings(st, airflow_mode=AIRFLOW_MODE_VAR, airflow_value=pct)

    async def async_set_auto_heater(self, on: bool, *, state: Optional[AtmosState] = None) -> None:
        """Enable/disable the auto comfort heater (on/off only; temp is installer)."""
        st = state or await self.async_get_state()
        await self._apply_home_settings(st, auto_heater=bool(on))

    async def async_set_boost_duration(self, minutes: int, *, state: Optional[AtmosState] = None) -> None:
        """Set boost run-on duration (20/40/60/720 minutes)."""
        if int(minutes) not in BOOST_MINUTES_OPTIONS:
            raise ValueError(f"boost minutes must be one of {BOOST_MINUTES_OPTIONS}")
        st = state or await self.async_get_state()
        await self._apply_home_settings(st, boost_minutes=int(minutes))

    async def async_set_filter_period(self, months: int, *, state: Optional[AtmosState] = None) -> None:
        """Set the filter reset period (12/24/36/48/60 months)."""
        if int(months) not in FILTER_MONTHS_OPTIONS:
            raise ValueError(f"filter months must be one of {FILTER_MONTHS_OPTIONS}")
        st = state or await self.async_get_state()
        await self._apply_home_settings(st, filter_months=int(months))

    async def _apply_home_settings(
        self,
        state: AtmosState,
        *,
        airflow_mode: Optional[str] = None,
        airflow_value: Optional[int] = None,
        auto_heater: Optional[bool] = None,
        boost_minutes: Optional[int] = None,
        filter_months: Optional[int] = None,
        summer_mode: Optional[bool] = None,
    ) -> None:
        """Read-modify-write the whole home block (SetHomeSettings rewrites all of it)."""
        mode = airflow_mode if airflow_mode is not None else (
            AIRFLOW_MODE_VAR if state.airflow_is_variable else AIRFLOW_MODE_SET
        )
        value = airflow_value if airflow_value is not None else state.airflow_value
        heater = auto_heater if auto_heater is not None else state.auto_heater_on
        mins = boost_minutes if boost_minutes is not None else state.boost_minutes
        months = filter_months if filter_months is not None else state.filter_reset_months
        summer = summer_mode if summer_mode is not None else state.summer_mode_enabled

        payload = {
            "command": CMD_SET_HOME_SETTINGS,
            "settings": {
                "airflow": {"mode": mode, "value": int(value)},
                "heater": {"autoActive": 1 if heater else 0},
                "boost": {"mins": int(mins)},
                "filter": {"resetMonths": int(months)},
                "summerBypass": {"summerShutdown": 1 if summer else 0},
            },
        }
        self._check(await self._request(payload), "SetHomeSettings")

    # ---------------- installer / commissioning (gated, default-off) ----------------

    def _require_installer(self) -> None:
        if not self._allow_installer:
            raise AtmosInstallerLockedError(
                "installer/commissioning writes are disabled; "
                "construct AtmosClient(allow_installer=True) to enable"
            )

    async def async_set_installer_settings(
        self,
        state: AtmosState,
        *,
        airflow_mode: Optional[str] = None,
        airflow_value: Optional[int] = None,
        auto_heater: Optional[bool] = None,
        heater_temperature: Optional[int] = None,
        boost_minutes: Optional[int] = None,
        filter_months: Optional[int] = None,
        summer_mode: Optional[bool] = None,
        summer_temperature: Optional[int] = None,
        twin_spigot: Optional[bool] = None,
    ) -> None:
        """Write the full installer block (RMW). GATED. Affects commissioning setpoints."""
        self._require_installer()
        mode = airflow_mode if airflow_mode is not None else (
            AIRFLOW_MODE_VAR if state.airflow_is_variable else AIRFLOW_MODE_SET
        )
        value = airflow_value if airflow_value is not None else state.airflow_value
        heater = auto_heater if auto_heater is not None else state.auto_heater_on
        htemp = heater_temperature if heater_temperature is not None else state.heater_temperature
        mins = boost_minutes if boost_minutes is not None else state.boost_minutes
        months = filter_months if filter_months is not None else state.filter_reset_months
        summer = summer_mode if summer_mode is not None else state.summer_mode_enabled
        stemp = summer_temperature if summer_temperature is not None else state.summer_temperature
        spigot = 2 if (twin_spigot if twin_spigot is not None else state.spigot_type == 2) else 1

        if not (HEATER_TEMP_MIN <= int(htemp) <= HEATER_TEMP_MAX):
            raise ValueError(f"heater temperature out of range {HEATER_TEMP_MIN}..{HEATER_TEMP_MAX}")
        if not (SUMMER_TEMP_MIN <= int(stemp) <= SUMMER_TEMP_MAX):
            raise ValueError(f"summer temperature out of range {SUMMER_TEMP_MIN}..{SUMMER_TEMP_MAX}")

        payload = {
            "command": CMD_SET_INSTALLER_SETTINGS,
            "settings": {
                "airflow": {"mode": mode, "value": int(value)},
                "heater": {"autoActive": 1 if heater else 0, "temperature": int(htemp)},
                "boost": {"mins": int(mins)},
                "filter": {"resetMonths": int(months)},
                "summerBypass": {"temperature": int(stemp), "summerShutdown": 1 if summer else 0},
                "spigot": {"type": spigot},
            },
        }
        self._check(await self._request(payload), "SetInstallerSettings")

    async def async_set_spigot_type(self, twin: bool) -> None:
        """Set spigot type (installer). GATED."""
        self._require_installer()
        self._check(
            await self._request({"command": CMD_SET_SPIGOT_TYPE, "type": 2 if twin else 1}),
            "SetSpigotType",
        )

    async def async_restore_home_defaults(self) -> None:
        self._require_installer()
        self._check(await self._request({"command": CMD_RESTORE_HOME_DEFAULTS}), CMD_RESTORE_HOME_DEFAULTS)

    async def async_restore_installer_defaults(self) -> None:
        self._require_installer()
        self._check(await self._request({"command": CMD_RESTORE_INSTALLER_DEFAULTS}), CMD_RESTORE_INSTALLER_DEFAULTS)

    async def async_restore_commissioning_defaults(self) -> None:
        self._require_installer()
        self._check(
            await self._request({"command": CMD_RESTORE_COMMISSIONING_DEFAULTS}),
            CMD_RESTORE_COMMISSIONING_DEFAULTS,
        )
