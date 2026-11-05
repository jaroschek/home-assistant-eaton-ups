"""Tests for UPS device identifier fallbacks."""

import pytest

from custom_components.eaton_ups.const import (
    SNMP_OID_IDENT_FIRMWARE_VERSION,
    SNMP_OID_IDENT_FIRMWARE_VERSION_XUPS,
    SNMP_OID_IDENT_PART_NUMBER,
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


@pytest.mark.parametrize(
    ("field", "oid"),
    [
        pytest.param("model", SNMP_OID_IDENT_PART_NUMBER, id="model"),
        pytest.param("serial_number", SERIAL, id="serial-number"),
        pytest.param("sw_version", SNMP_OID_IDENT_FIRMWARE_VERSION, id="sw-version"),
        pytest.param(
            "sw_version", SNMP_OID_IDENT_FIRMWARE_VERSION_XUPS, id="sw-version-xups"
        ),
    ],
)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(214, "214", id="int"),
        pytest.param(2.14, "2.14", id="float"),
        pytest.param("02.14", "02.14", id="str"),
    ],
)
async def test_device_info_fields_are_text(
    coordinator: SnmpCoordinator,
    field: str,
    oid: str,
    value: int | float | str,
    expected: str,
) -> None:
    """The device registry requires text, and SNMP values can be numbers."""
    coordinator.data = {oid: value}
    sensor = SnmpOutputCumulativeEnergySensorEntity(coordinator)
    assert sensor.device_info[field] == expected


async def test_device_info_missing_fields_stay_none(
    coordinator: SnmpCoordinator,
) -> None:
    """Missing values must not become the text 'None'."""
    coordinator.data = {SNMP_OID_IDENT_FIRMWARE_VERSION: ""}
    device_info = SnmpOutputCumulativeEnergySensorEntity(coordinator).device_info
    assert device_info["model"] is None
    assert device_info["sw_version"] is None
