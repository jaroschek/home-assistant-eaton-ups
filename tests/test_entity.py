"""Tests for UPS device identifier fallbacks."""

import pytest

from custom_components.eaton_ups.const import (
    SNMP_OID_IDENT_SERIAL_NUMBER,
    SNMP_OID_IDENT_SERIAL_NUMBER_XUPS,
)
from custom_components.eaton_ups.coordinator import SnmpCoordinator
from custom_components.eaton_ups.sensor import SnmpOutputCumulativeEnergySensorEntity

SERIAL = SNMP_OID_IDENT_SERIAL_NUMBER
ALTERNATE_SERIAL = SNMP_OID_IDENT_SERIAL_NUMBER_XUPS


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            {SERIAL: "serial", ALTERNATE_SERIAL: "alternate"}, "serial", id="serial"
        ),
        pytest.param(
            {SERIAL: "", ALTERNATE_SERIAL: "alternate"}, "alternate", id="empty-serial"
        ),
        pytest.param(
            {SERIAL: None, ALTERNATE_SERIAL: "alternate"}, "alternate", id="none-serial"
        ),
        pytest.param(
            {ALTERNATE_SERIAL: "alternate"}, "alternate", id="alternate-serial"
        ),
        pytest.param({SERIAL: "", ALTERNATE_SERIAL: ""}, "192.0.2.1", id="host"),
    ],
)
async def test_identifier_fallbacks(
    coordinator: SnmpCoordinator, data: dict[str, str | None], expected: str
) -> None:
    """Device identifiers must use nonempty fallback metadata."""
    coordinator.data = data
    sensor = SnmpOutputCumulativeEnergySensorEntity(coordinator)
    assert sensor.identifier == expected
    assert sensor.device_info["identifiers"] == {("eaton_ups", expected)}
