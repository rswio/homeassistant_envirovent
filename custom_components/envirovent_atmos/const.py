"""Constants for the EnviroVent ATMOS integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "envirovent_atmos"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_HOST = ""  # no baked-in default — enter your unit's reserved IP (or use discovery)
DEFAULT_PORT = 1337
DEFAULT_SCAN_INTERVAL = 30  # seconds; unit accepts one client at a time — poll gently
MIN_SCAN_INTERVAL = 15

MANUFACTURER = "EnviroVent"
MODEL = "ATMOS PIV (ATL-A)"

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.BUTTON,
]
