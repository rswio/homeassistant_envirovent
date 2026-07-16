"""Typed data model for the ATMOS PIV state.

Parsing mirrors PivGetCurrentSettingsResult / PivHomeUnitSettings in the app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .const import AIRFLOW_MODE_VAR


def _as_bool(obj: Optional[Dict[str, Any]], key: str, default: bool = False) -> bool:
    """Wire booleans are ints; 1 == True (matches BaseResult.getBoolean)."""
    if not obj:
        return default
    try:
        return int(obj.get(key, 1 if default else 0)) == 1
    except (TypeError, ValueError):
        return default


def _as_int(obj: Optional[Dict[str, Any]], key: str, default: int = 0) -> int:
    if not obj:
        return default
    try:
        return int(obj.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AirflowMap:
    """One calibration point from airflowConfiguration.maps (wire mark is 1-based)."""

    mark: int
    percent: int


@dataclass
class AtmosState:
    """Decoded GetCurrentSettings response — the whole readable state."""

    raw: Dict[str, Any] = field(repr=False)
    success: bool = False
    error: str = ""
    unit_type: Optional[str] = None
    software_version: Optional[str] = None

    # airflow
    airflow_is_variable: bool = False
    airflow_value: int = 0                 # raw wire value (preset step OR percent)
    airflow_active: bool = False
    preset_speed: Optional[int] = None     # 1..max_preset in SET mode, else None
    variable_percent: Optional[int] = None  # percent in VAR mode, else None
    max_preset: int = 0
    variable_min_percent: int = 0
    variable_max_percent: int = 0
    presets: Dict[int, int] = field(default_factory=dict)  # speed(1..N) -> percent
    airflow_maps: List[AirflowMap] = field(default_factory=list)

    # boost
    boost_on: bool = False
    boost_input_on: bool = False
    boost_minutes: int = 0

    # filter
    filter_remaining_days: int = 0
    filter_reset_months: int = 0
    filter_needs_changing: bool = False

    # heater (auto comfort heater)
    auto_heater_on: bool = False
    heater_temperature: int = 0            # setpoint (installer)

    # summer bypass
    summer_active: bool = False            # currently bypassing
    summer_mode_enabled: bool = False      # summerShutdown toggle
    summer_temperature: int = 0            # setpoint (installer)

    # misc
    kick_up_active: bool = False
    spigot_type: int = 1
    spigot_can_change: bool = False
    hours_run: int = 0
    any_modes_on: bool = False

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "AtmosState":
        settings = data.get("settings") or {}
        airflow = settings.get("airflow") or {}
        boost = settings.get("boost") or {}
        boost_input = settings.get("boostInput") or {}
        filt = settings.get("filter") or {}
        heater = settings.get("heater") or {}
        summer = settings.get("summerBypass") or {}
        kick = settings.get("kickUp") or {}
        spigot = settings.get("spigot") or {}

        # airflow map -> presets & variable min/max (mirrors the app)
        maps: List[AirflowMap] = []
        raw_maps = ((data.get("airflowConfiguration") or {}).get("maps")) or []
        for m in raw_maps:
            maps.append(AirflowMap(mark=_as_int(m, "mark"), percent=_as_int(m, "percent")))
        presets: Dict[int, int] = {}
        var_min = var_max = 0
        max_preset = 0
        if maps:
            var_min = maps[0].percent
            var_max = maps[-1].percent
            middle = maps[1:-1]                     # strip first & last
            for i, mp in enumerate(middle, start=1):
                presets[i] = mp.percent
            max_preset = len(middle)

        mode_str = str(airflow.get("mode", "")).strip()
        is_var = mode_str.lower() == "var" if mode_str else _bool_mode_default(airflow)
        value = _as_int(airflow, "value")

        preset_speed: Optional[int] = None
        variable_percent: Optional[int] = None
        if is_var:
            variable_percent = value
        else:
            preset_speed = value

        boost_input_on = _as_bool(boost_input, "enabled")
        auto_heater = _as_bool(heater, "autoActive")
        summer_active = _as_bool(summer, "active")
        kick_up = _as_bool(kick, "active")
        # app aggregate (boost.enabled deliberately excluded)
        any_modes = boost_input_on or auto_heater or summer_active or kick_up

        filter_days = _as_int(filt, "remainingDays")
        spigot_type = 2 if _as_int(spigot, "type", 1) == 2 else 1

        return cls(
            raw=data,
            success=_as_bool(data, "success"),
            error=str(data.get("error", "") or ""),
            unit_type=data.get("unitType"),
            software_version=data.get("softwareVersion"),
            airflow_is_variable=is_var,
            airflow_value=value,
            airflow_active=_as_bool(airflow, "active"),
            preset_speed=preset_speed,
            variable_percent=variable_percent,
            max_preset=max_preset,
            variable_min_percent=var_min,
            variable_max_percent=var_max,
            presets=presets,
            airflow_maps=maps,
            boost_on=_as_bool(boost, "enabled"),
            boost_input_on=boost_input_on,
            boost_minutes=_as_int(boost, "mins"),
            filter_remaining_days=filter_days,
            filter_reset_months=_as_int(filt, "resetMonths"),
            filter_needs_changing=filter_days == 0,
            auto_heater_on=auto_heater,
            heater_temperature=_as_int(heater, "temperature"),
            summer_active=summer_active,
            summer_mode_enabled=_as_bool(summer, "summerShutdown"),
            summer_temperature=_as_int(summer, "temperature"),
            kick_up_active=kick_up,
            spigot_type=spigot_type,
            spigot_can_change=_as_bool(spigot, "canChange"),
            hours_run=_as_int(settings, "hoursRun"),
            any_modes_on=any_modes,
        )

    def percent_for_speed(self, speed: int) -> Optional[int]:
        """Airflow percentage for a given preset speed (1..max_preset)."""
        return self.presets.get(speed)


def _bool_mode_default(airflow: Dict[str, Any]) -> bool:
    """If mode is missing, fall back to SET (preset) like the app default."""
    return False
