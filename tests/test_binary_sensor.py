"""Tests for UPS battery alerts with missing status."""

from unittest.mock import patch

import pytest

from custom_components.eaton_ups.binary_sensor import SnmpBatteryFailureSensorEntity
from custom_components.eaton_ups.const import SNMP_OID_BATTERY_FAILURE
from custom_components.eaton_ups.coordinator import SnmpCoordinator


@pytest.mark.parametrize(
    ("value", "expected", "created", "dismissed"),
    [
        pytest.param(None, None, False, False, id="missing"),
        pytest.param(0, False, False, True, id="clear"),
        pytest.param(1, True, True, False, id="failure"),
    ],
)
async def test_battery_alert_missing_status(
    coordinator: SnmpCoordinator,
    value: int | None,
    expected: bool | None,
    created: bool,
    dismissed: bool,
) -> None:
    """An unavailable status must stay unknown and preserve an existing alert."""
    coordinator.data[SNMP_OID_BATTERY_FAILURE] = value
    with (
        patch(
            "custom_components.eaton_ups.binary_sensor.persistent_notification.create"
        ) as create,
        patch(
            "custom_components.eaton_ups.binary_sensor.persistent_notification.dismiss"
        ) as dismiss,
    ):
        sensor = SnmpBatteryFailureSensorEntity(coordinator)
        assert sensor.is_on is expected
        assert create.called is created
        assert dismiss.called is dismissed
