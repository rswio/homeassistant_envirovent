"""CLI test harness for the ATMOS PIV client.

    python -m envirovent_atmos.probe 192.168.1.50            # dump state
    python -m envirovent_atmos.probe 192.168.1.50 raw        # raw JSON
    python -m envirovent_atmos.probe 192.168.1.50 boost on   # write tests
    python -m envirovent_atmos.probe 192.168.1.50 speed 3
    python -m envirovent_atmos.probe 192.168.1.50 variable 55
    python -m envirovent_atmos.probe 192.168.1.50 auto-heater off
    python -m envirovent_atmos.probe 192.168.1.50 boost-duration 40
    python -m envirovent_atmos.probe 192.168.1.50 filter-period 24
    python -m envirovent_atmos.probe 192.168.1.50 reset-filter
    python -m envirovent_atmos.probe 192.168.1.50 boost-test  # reversible round-trip
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from .client import AtmosClient, AtmosError
from .const import DEFAULT_PORT, DEFAULT_TIMEOUT


def _onoff(v: str) -> bool:
    return str(v).lower() in ("1", "on", "true", "yes", "enable", "enabled")


def _print_state(st) -> None:
    airflow = (
        f"variable {st.variable_percent}% (range {st.variable_min_percent}-{st.variable_max_percent}%)"
        if st.airflow_is_variable
        else f"preset speed {st.preset_speed}/{st.max_preset} ({st.percent_for_speed(st.preset_speed)}%)"
    )
    modes = [n for n, on in (
        ("Airflow", st.airflow_active), ("Boost", st.boost_on),
        ("BoostInput", st.boost_input_on), ("AutoHeater", st.auto_heater_on),
        ("SummerBypass", st.summer_active), ("KickUp", st.kick_up_active),
    ) if on]
    print(f"  Unit:            {st.unit_type}  sw {st.software_version}  (success={st.success})")
    print(f"  Airflow:         {airflow}   active={st.airflow_active}")
    print(f"  Preset map:      {st.presets}")
    print(f"  Boost:           {'ON' if st.boost_on else 'off'}  duration={st.boost_minutes} min  input={st.boost_input_on}")
    print(f"  Auto heater:     {'ON' if st.auto_heater_on else 'off'}  setpoint={st.heater_temperature}C")
    print(f"  Summer mode:     enabled={st.summer_mode_enabled}  active={st.summer_active}  setpoint={st.summer_temperature}C")
    print(f"  Kick up:         {st.kick_up_active}")
    print(f"  Filter:          {st.filter_remaining_days} days remaining  period={st.filter_reset_months} months  needsChange={st.filter_needs_changing}")
    print(f"  Spigot:          type={st.spigot_type} ({'twin' if st.spigot_type == 2 else 'single'})  canChange={st.spigot_can_change}")
    print(f"  Hours run:       {st.hours_run}")
    print(f"  Modes on:        {', '.join(modes) or '(none)'}   anyModesOn={st.any_modes_on}")


async def _run(args: argparse.Namespace) -> int:
    client = AtmosClient(args.host, args.port, timeout=args.timeout)
    cmd = args.command
    try:
        if cmd in (None, "state"):
            _print_state(await client.async_get_state())
        elif cmd == "raw":
            print(json.dumps(await client.async_get_raw(), indent=2, sort_keys=True))
        elif cmd == "boost":
            await client.async_set_boost(_onoff(args.arg))
            print(f"boost -> {args.arg}")
            _print_state(await client.async_get_state())
        elif cmd == "summer":
            await client.async_set_summer_mode(_onoff(args.arg))
            print(f"summer -> {args.arg}")
        elif cmd == "speed":
            await client.async_set_preset_speed(int(args.arg))
            print(f"preset speed -> {args.arg}")
            _print_state(await client.async_get_state())
        elif cmd == "variable":
            await client.async_set_variable_airflow(int(args.arg))
            print(f"variable airflow -> {args.arg}%")
            _print_state(await client.async_get_state())
        elif cmd == "auto-heater":
            await client.async_set_auto_heater(_onoff(args.arg))
            print(f"auto heater -> {args.arg}")
        elif cmd == "boost-duration":
            await client.async_set_boost_duration(int(args.arg))
            print(f"boost duration -> {args.arg} min")
        elif cmd == "filter-period":
            await client.async_set_filter_period(int(args.arg))
            print(f"filter period -> {args.arg} months")
        elif cmd == "reset-filter":
            await client.async_reset_filter()
            print("filter counter reset")
        elif cmd == "boost-test":
            print("Reversible boost round-trip test:")
            before = await client.async_get_state()
            print(f"  initial boost = {before.boost_on}")
            await client.async_set_boost(True)
            mid = await client.async_get_state()
            print(f"  after ON      = {mid.boost_on}")
            await client.async_set_boost(False)
            after = await client.async_get_state()
            print(f"  after OFF     = {after.boost_on}")
            ok = mid.boost_on and not after.boost_on
            print(f"  RESULT: {'PASS' if ok else 'CHECK'} (restored to boost={after.boost_on})")
            return 0 if ok else 2
        else:
            print(f"unknown command: {cmd}", file=sys.stderr)
            return 2
        return 0
    except AtmosError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="envirovent_atmos.probe", description="ATMOS PIV local client test harness")
    p.add_argument("host")
    p.add_argument("command", nargs="?", default=None)
    p.add_argument("arg", nargs="?", default=None)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = p.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
