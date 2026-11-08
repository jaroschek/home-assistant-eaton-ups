"""Tests for the alarm sensors, alarm decoding and alarm table polling."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.eaton_ups.api import SnmpApi
from custom_components.eaton_ups.binary_sensor import SnmpAlarmActiveSensorEntity
from custom_components.eaton_ups.const import (
    SNMP_OID_ALARM_DESCR,
    SNMP_OID_ALARM_DESCR_XUPS,
    SNMP_OID_ALARMS_PRESENT,
    SNMP_OID_ALARMS_PRESENT_XUPS,
)
from custom_components.eaton_ups.coordinator import SnmpCoordinator
from custom_components.eaton_ups.sensor import (
    SnmpActiveAlarmsSensorEntity,
    decode_alarms,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

STD_ROW = SNMP_OID_ALARM_DESCR.replace("index", "")
XUPS_ROW = SNMP_OID_ALARM_DESCR_XUPS.replace("index", "")


def test_decode_known_and_unknown_alarms() -> None:
    """Known alarm OIDs get names; unknown ones keep their raw OID."""
    data = {
        f"{STD_ROW}1": "1.3.6.1.2.1.33.1.6.3.3",
        f"{XUPS_ROW}10": "1.3.6.1.4.1.534.1.7.17",
        f"{XUPS_ROW}2": ".1.3.6.1.4.1.534.1.7.6",
        f"{XUPS_ROW}3": "1.3.6.1.4.1.534.1.7.999",
    }
    assert decode_alarms(data) == [
        "Low Battery",
        "Return From Low Battery",
        "1.3.6.1.4.1.534.1.7.999",
        "On Inverter",
    ]


def test_decode_deduplicates_across_tables() -> None:
    """An alarm reported by both tables is listed once."""
    data = {
        f"{STD_ROW}1": "1.3.6.1.2.1.33.1.6.3.2",
        f"{XUPS_ROW}1": "1.3.6.1.4.1.534.1.7.3",
    }
    assert decode_alarms(data) == ["On Battery"]


def test_decode_no_alarms() -> None:
    """An empty table decodes to no alarms."""
    assert decode_alarms({SNMP_OID_ALARMS_PRESENT: 0}) == []


FAULT = "1.3.6.1.4.1.534.1.7.8"
INFO = "1.3.6.1.4.1.534.1.7.17"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({}, None, id="unsupported"),
        pytest.param({SNMP_OID_ALARMS_PRESENT: 0}, False, id="none"),
        pytest.param(
            {
                SNMP_OID_ALARMS_PRESENT_XUPS: 2,
                f"{XUPS_ROW}1": INFO,
                f"{XUPS_ROW}2": "1.3.6.1.4.1.534.1.7.6",
            },
            False,
            id="informational-only",
        ),
        pytest.param(
            {
                SNMP_OID_ALARMS_PRESENT_XUPS: 2,
                f"{XUPS_ROW}1": INFO,
                f"{XUPS_ROW}2": FAULT,
            },
            True,
            id="fault",
        ),
        pytest.param(
            {
                SNMP_OID_ALARMS_PRESENT_XUPS: 1,
                f"{XUPS_ROW}1": ".1.3.6.1.4.1.534.1.7.999",
            },
            True,
            id="unknown-oid",
        ),
        pytest.param(
            {SNMP_OID_ALARMS_PRESENT: 1, f"{STD_ROW}1": "1.3.6.1.2.1.33.1.6.3.24"},
            False,
            id="standard-test-in-progress",
        ),
    ],
)
async def test_alarm_active_binary_sensor(
    coordinator: SnmpCoordinator, data: dict[str, int | str], expected: bool | None
) -> None:
    """Only fault rows turn the sensor on, and no counts leave it unknown."""
    coordinator.data.update(data)
    with (
        patch(
            "custom_components.eaton_ups.binary_sensor.persistent_notification.create"
        ),
        patch(
            "custom_components.eaton_ups.binary_sensor.persistent_notification.dismiss"
        ),
    ):
        assert SnmpAlarmActiveSensorEntity(coordinator).is_on is expected


async def test_alarm_sensors(coordinator: SnmpCoordinator) -> None:
    """The decoded sensor lists every alarm, informational or not."""
    coordinator.data.update(
        {
            SNMP_OID_ALARMS_PRESENT_XUPS: 2,
            f"{XUPS_ROW}34": "1.3.6.1.4.1.534.1.7.6",
            f"{XUPS_ROW}37": "1.3.6.1.4.1.534.1.7.17",
        }
    )
    sensor = SnmpActiveAlarmsSensorEntity(coordinator)
    assert sensor.native_value == 2
    assert sensor.extra_state_attributes["alarms"] == [
        "Return From Low Battery",
        "On Inverter",
    ]


async def test_alarm_tables_read_only_when_present(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Alarm rows are fetched for non-zero counts only."""
    api = MagicMock(spec=SnmpApi)
    api.get.return_value = {SNMP_OID_ALARMS_PRESENT: 0, SNMP_OID_ALARMS_PRESENT_XUPS: 1}
    api.get_bulk.return_value = [{f"{XUPS_ROW}5": "1.3.6.1.4.1.534.1.7.3"}]
    coordinator = SnmpCoordinator(hass, entry, api)
    await coordinator.async_refresh()
    api.get_bulk.assert_called_once_with([XUPS_ROW], 1)
    assert coordinator.data[f"{XUPS_ROW}5"] == "1.3.6.1.4.1.534.1.7.3"
