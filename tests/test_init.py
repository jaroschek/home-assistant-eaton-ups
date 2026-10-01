"""Tests for recoverable setup failures."""

from unittest.mock import AsyncMock, MagicMock, patch

from pysnmp.error import PySnmpError
import pytest

from custom_components import eaton_ups as integration
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


async def test_unresolved_host_retries(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Home Assistant must retry an entry whose hostname cannot be resolved."""
    with (
        patch.object(
            integration, "async_get_snmp_engine", AsyncMock(return_value=MagicMock())
        ),
        patch.object(
            integration.SnmpApi,
            "setup",
            AsyncMock(side_effect=PySnmpError("Unknown host")),
        ),
        pytest.raises(ConfigEntryNotReady, match="Unable to resolve SNMP host"),
    ):
        await integration.async_setup_entry(hass, entry)
