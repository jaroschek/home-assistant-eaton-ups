"""Tests for publishing complete SNMP refreshes."""

from unittest.mock import MagicMock

from pysnmp.error import PySnmpError
import pytest

from custom_components.eaton_ups.api import SnmpApi
from custom_components.eaton_ups.const import (
    SNMP_OID_INPUT_NUM_PHASES,
    SNMP_OID_OUTPUT_NUM_PHASES,
)
from custom_components.eaton_ups.coordinator import SnmpCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

BASE_REPLIES = [
    {SNMP_OID_INPUT_NUM_PHASES: 1, SNMP_OID_OUTPUT_NUM_PHASES: 1},
]


@pytest.fixture
def snmp_api() -> MagicMock:
    """Provide a mocked SNMP API."""
    return MagicMock(spec=SnmpApi)


@pytest.fixture
def coordinator(
    hass: HomeAssistant, entry: ConfigEntry, snmp_api: MagicMock
) -> SnmpCoordinator:
    """Provide a coordinator with its config entry explicitly set."""
    return SnmpCoordinator(hass, entry, snmp_api)


async def test_refresh_drops_missing_readings(
    coordinator: SnmpCoordinator, snmp_api: MagicMock
) -> None:
    """Values missing from a successful refresh must not retain stale readings."""
    snmp_api.get.side_effect = [dict(reply) for _ in range(2) for reply in BASE_REPLIES]
    snmp_api.get_bulk.side_effect = [[{"input": 230}], [{"output": 240}], [], []]
    await coordinator.async_refresh()
    previous = coordinator.data
    assert previous["input"] == 230
    assert previous["output"] == 240

    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert "input" not in coordinator.data
    assert "output" not in coordinator.data
    assert previous["input"] == 230


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError("Timeout"), id="snmp-error"),
        pytest.param(PySnmpError("Transport failed"), id="transport-error"),
    ],
)
async def test_failed_refresh_preserves_previous_data(
    coordinator: SnmpCoordinator, snmp_api: MagicMock, error: Exception
) -> None:
    """A failed table read must not publish part of a refresh."""
    snmp_api.get.side_effect = [
        *[dict(reply) for reply in BASE_REPLIES],
        *[dict(reply) | {"new": 99} for reply in BASE_REPLIES],
    ]
    snmp_api.get_bulk.side_effect = [[{"input": 230}], [{"output": 240}], error]
    await coordinator.async_refresh()
    previous = dict(coordinator.data)
    await coordinator.async_refresh()

    assert not coordinator.last_update_success
    assert coordinator.data == previous
    assert "new" not in coordinator.data


async def test_config_entry_set(
    coordinator: SnmpCoordinator, entry: ConfigEntry
) -> None:
    """Entity metadata must have access to the config entry outside setup."""
    assert coordinator.config_entry is entry
