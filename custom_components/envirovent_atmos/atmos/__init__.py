"""Standalone async client for EnviroVent ATMOS PIV units (local TCP/1337 JSON).

Reverse-engineered and unofficial. See research/protocol-spec.md.
"""
from __future__ import annotations

from .client import (
    AtmosClient,
    AtmosCommandError,
    AtmosConnectionError,
    AtmosError,
    AtmosInstallerLockedError,
    AtmosResponseError,
)
from .models import AirflowMap, AtmosState

__all__ = [
    "AtmosClient",
    "AtmosState",
    "AirflowMap",
    "AtmosError",
    "AtmosConnectionError",
    "AtmosResponseError",
    "AtmosCommandError",
    "AtmosInstallerLockedError",
]

__version__ = "0.1.0"
