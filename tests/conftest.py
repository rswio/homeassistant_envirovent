"""Test fixtures for the EnviroVent ATMOS integration."""
import pytest

# A real GetCurrentSettings response captured live from the unit (sw 2.4).
SAMPLE_RESPONSE = {
    "success": 1,
    "error": "",
    "unitType": "PIV",
    "softwareVersion": "2.4",
    "settings": {
        "airflow": {"active": 1, "mode": "SET", "value": 4},
        "boost": {"enabled": 0, "mins": 20},
        "boostInput": {"enabled": 0},
        "filter": {"remainingDays": 1813, "resetMonths": 60},
        "heater": {"autoActive": 1, "temperature": 10},
        "hoursRun": 6346,
        "kickUp": {"active": 1},
        "spigot": {"canChange": 1, "type": 1},
        "summerBypass": {"active": 1, "summerShutdown": 1, "temperature": 25},
    },
    "airflowConfiguration": {
        "maps": [
            {"mark": 1, "percent": 8},
            {"mark": 2, "percent": 30},
            {"mark": 3, "percent": 44},
            {"mark": 4, "percent": 57},
            {"mark": 5, "percent": 74},
            {"mark": 6, "percent": 100},
        ]
    },
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield
