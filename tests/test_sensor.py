"""Tests for missing UPS measurements."""

from unittest.mock import patch

import pytest

from custom_components.eaton_ups.const import SNMP_OID_OUTPUT_CUMULATIVE_ENERGY
from custom_components.eaton_ups.coordinator import SnmpCoordinator
from custom_components.eaton_ups.sensor import SnmpOutputCumulativeEnergySensorEntity

READING = SNMP_OID_OUTPUT_CUMULATIVE_ENERGY


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({}, None, id="missing"),
        pytest.param({READING: None}, None, id="none"),
        pytest.param({READING: ""}, None, id="empty"),
        pytest.param({READING: 0}, 0, id="zero"),
        pytest.param({READING: 1234}, 1234, id="measurement"),
    ],
)
async def test_sensor_readings(
    coordinator: SnmpCoordinator,
    data: dict[str, int | str | None],
    expected: float | None,
) -> None:
    """Unknown measurements must not become zeros or cause arithmetic errors."""
    coordinator.data.update(data)
    sensor = SnmpOutputCumulativeEnergySensorEntity(coordinator)
    assert sensor.native_value == expected


async def test_sensor_update_missing(coordinator: SnmpCoordinator) -> None:
    """An existing sensor must become unknown when its reading disappears."""
    coordinator.data[READING] = 1234
    sensor = SnmpOutputCumulativeEnergySensorEntity(coordinator)
    coordinator.data.pop(READING)
    with patch(
        "homeassistant.helpers.entity.Entity.async_write_ha_state"
    ) as write_state:
        sensor._handle_coordinator_update()
        write_state.assert_called_once()
    assert sensor.native_value is None
