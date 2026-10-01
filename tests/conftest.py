"""Local Home Assistant fixtures for the Eaton regression tests."""

from collections.abc import AsyncGenerator
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

from custom_components.eaton_ups.const import (
    SNMP_OID_IDENT_SERIAL_NUMBER,
    SNMP_OID_IDENT_SYSTEM_NAME,
)
from custom_components.eaton_ups.coordinator import SnmpCoordinator
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.fixture
async def hass(tmp_path: Path) -> AsyncGenerator[HomeAssistant]:
    """Provide Home Assistant without starting integrations or writing config."""
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    with patch.object(instance.config_entries, "_async_schedule_save"):
        yield instance
        await instance.async_stop()


@pytest.fixture
def entry(hass: HomeAssistant) -> ConfigEntry:
    """Provide a registered SNMPv1 entry."""
    config_entry = ConfigEntry(
        domain="eaton_ups",
        title="Eaton",
        data={"host": "192.0.2.1", "version": "1", "community": "public"},
        options={},
        source="user",
        version=1,
        minor_version=1,
        unique_id="test-device",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )
    hass.config_entries._entries[config_entry.entry_id] = config_entry
    return config_entry


@pytest.fixture
def coordinator(hass: HomeAssistant, entry: ConfigEntry) -> SnmpCoordinator:
    """Provide entity data independently of the coordinator implementation."""
    instance = MagicMock(spec=SnmpCoordinator)
    instance.hass = hass
    instance.config_entry = entry
    instance.last_update_success = True
    instance.data = {
        SNMP_OID_IDENT_SERIAL_NUMBER: "serial",
        SNMP_OID_IDENT_SYSTEM_NAME: "UPS",
    }
    return instance
