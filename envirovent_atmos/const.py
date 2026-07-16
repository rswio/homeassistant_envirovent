"""Constants for the EnviroVent ATMOS PIV local protocol.

Reverse-engineered from the myenvirovent Android app (v1.9) and confirmed live.
See research/protocol-spec.md for the full protocol description.
"""
from __future__ import annotations

DEFAULT_PORT = 1337
DEFAULT_TIMEOUT = 10.0          # seconds (app uses SocketTimeout = 10000 ms)
DEFAULT_RETRIES = 2             # extra attempts on connection failure/timeout
DEFAULT_RETRY_DELAY = 0.6       # seconds, multiplied by attempt number

# --- Commands (value of the "command" key) ---
CMD_GET_CURRENT_SETTINGS = "GetCurrentSettings"
CMD_GET_STATUS = "GetStatus"                       # empty payload for PIV; unused
CMD_SET_BOOST = "SetBoost"
CMD_SET_SUMMER_BYPASS = "SetSummerBypass"
CMD_SET_HOME_SETTINGS = "SetHomeSettings"
CMD_FILTER_MAINTENANCE_COMPLETE = "FilterMaintenanceComplete"
# installer / commissioning (gated, default-off)
CMD_SET_INSTALLER_SETTINGS = "SetInstallerSettings"
CMD_SET_SPIGOT_TYPE = "SetSpigotType"
CMD_RESTORE_HOME_DEFAULTS = "RestoreHomeSettingsToFactoryDefaults"
CMD_RESTORE_INSTALLER_DEFAULTS = "RestoreInstallerSettingsToFactoryDefaults"
CMD_RESTORE_COMMISSIONING_DEFAULTS = "RestoreCommissioningSettingsToFactoryDefaults"

# --- Airflow modes (wire strings) ---
AIRFLOW_MODE_SET = "SET"        # fixed preset speed
AIRFLOW_MODE_VAR = "VAR"        # variable percentage

# --- Value domains (resident-safe controls) ---
BOOST_MINUTES_OPTIONS = (20, 40, 60, 720)
FILTER_MONTHS_OPTIONS = (12, 24, 36, 48, 60)

# --- Installer-only value ranges ---
HEATER_TEMP_MIN, HEATER_TEMP_MAX = 5, 15
SUMMER_TEMP_MIN, SUMMER_TEMP_MAX = 18, 28
SPIGOT_SINGLE, SPIGOT_TWIN = 1, 2

# --- Response envelope keys ---
KEY_SUCCESS = "success"
KEY_NO_RESPONSE = "noresponse"
KEY_ERROR = "error"

UNIT_TYPE_PIV = "PIV"

# --- Discovery ---
ZEROCONF_SERVICE_TYPE = "_http._tcp.local."
AP_MODE_HOST = "192.168.1.1"
