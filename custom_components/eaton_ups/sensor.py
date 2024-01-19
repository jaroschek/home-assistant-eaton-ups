"""Support for Eaton UPS sensors."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import get_time_zone

from .const import (
    DOMAIN,
    SNMP_OID_BATTERY_ABM_STATUS,
    SNMP_OID_BATTERY_CAPACITY,
    SNMP_OID_BATTERY_CURRENT,
    SNMP_OID_BATTERY_LAST_REPLACED,
    SNMP_OID_BATTERY_REMAINING,
    SNMP_OID_BATTERY_TEST_STATUS,
    SNMP_OID_BATTERY_VOLTAGE,
    SNMP_OID_INPUT_CURRENT,
    SNMP_OID_INPUT_NAME,
    SNMP_OID_INPUT_NUM_PHASES,
    SNMP_OID_INPUT_SOURCE,
    SNMP_OID_INPUT_STATUS,
    SNMP_OID_INPUT_VOLTAGE,
    SNMP_OID_INPUT_WATTS,
    SNMP_OID_OUTPUT_CURRENT,
    SNMP_OID_OUTPUT_LOAD,
    SNMP_OID_OUTPUT_NAME,
    SNMP_OID_OUTPUT_NUM_PHASES,
    SNMP_OID_OUTPUT_SOURCE,
    SNMP_OID_OUTPUT_STATUS,
    SNMP_OID_OUTPUT_VOLTAGE,
    SNMP_OID_OUTPUT_WATTS,
    AbmStatus,
    BatteryTestStatus,
    InputSource,
    InputStatus,
    OutputSource,
    OutputStatus,
)
from .coordinator import SnmpCoordinator
from .entity import SnmpEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        SnmpBatteryVoltageSensorEntity(coordinator),
        # SnmpBatteryCurrentSensorEntity(coordinator),
        SnmpBatteryCapacitySensorEntity(coordinator),
        SnmpBatteryAbmStatusSensorEntity(coordinator),
        SnmpBatteryLastReplacedSensorEntity(coordinator),
        SnmpBatteryRemainingSensorEntity(coordinator),
        SnmpBatteryTestStatusSensorEntity(coordinator),
        SnmpInputSourceSensorEntity(coordinator),
        SnmpInputStatusSensorEntity(coordinator),
        SnmpOutputSourceSensorEntity(coordinator),
        SnmpOutputStatusSensorEntity(coordinator),
    ]

    for index in range(
        1,
        coordinator.data.get(SNMP_OID_INPUT_NUM_PHASES, 0) + 1,
    ):
        entities.append(SnmpInputVoltageSensorEntity(coordinator, index))
        # entities.append(SnmpInputCurrentSensorEntity(coordinator, index))
        # entities.append(SnmpInputWattsSensorEntity(coordinator, index))

    for index in range(
        1,
        coordinator.data.get(SNMP_OID_OUTPUT_NUM_PHASES, 0) + 1,
    ):
        entities.append(SnmpOutputVoltageSensorEntity(coordinator, index))
        entities.append(SnmpOutputCurrentSensorEntity(coordinator, index))
        entities.append(SnmpOutputWattsSensorEntity(coordinator, index))
        entities.append(SnmpOutputLoadSensorEntity(coordinator, index))

    async_add_entities(entities)


class SnmpSensorEntity(SnmpEntity, SensorEntity):
    """Representation of a Eaton UPS sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    _multiplier: float | None = None

    _default_value: float = 0.0

    def __init__(self, coordinator: SnmpCoordinator, index: str = "") -> None:
        """Initialize a Eaton UPS sensor."""
        super().__init__(coordinator, index)
        self._attr_native_value = self.coordinator.data.get(
            self._value_oid, self._default_value
        )
        if self._multiplier is not None:
            self._attr_native_value *= self._multiplier

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.get(
            self._value_oid, self._default_value
        )
        if self._multiplier is not None:
            self._attr_native_value *= self._multiplier

        super().async_write_ha_state()


class SnmpBatterySensorEntity(SnmpSensorEntity):
    """Representation of a Eaton UPS battery sensor."""

    _name_prefix = "Battery"


class SnmpBatteryVoltageSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery voltage sensor."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    _name_suffix = "Voltage"
    _value_oid = SNMP_OID_BATTERY_VOLTAGE


class SnmpBatteryCurrentSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery current sensor."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    _name_suffix = "Current"
    _value_oid = SNMP_OID_BATTERY_CURRENT


class SnmpBatteryCapacitySensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery watts sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    _name_suffix = "Capacity"
    _value_oid = SNMP_OID_BATTERY_CAPACITY


class SnmpBatteryAbmStatusSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery abm status sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_translation_key = "abm_status"
    _attr_options = [abm_status.value for abm_status in AbmStatus]

    _name_suffix = "ABM Status"
    _value_oid = SNMP_OID_BATTERY_ABM_STATUS


class SnmpBatteryLastReplacedSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery last replaced sensor."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_state_class = None

    _name_suffix = "Last Replaced"
    _value_oid = SNMP_OID_BATTERY_LAST_REPLACED

    @property
    def native_value(self) -> date:
        """Return the value reported by the sensor."""
        return (
            datetime.strptime(self._attr_native_value, "%m/%d/%Y")
            .replace(tzinfo=get_time_zone(self.coordinator.hass.config.time_zone))
            .date()
        )


class SnmpBatteryRemainingSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery last replaced sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    _name_suffix = "Remaining"
    _value_oid = SNMP_OID_BATTERY_REMAINING


class SnmpBatteryTestStatusSensorEntity(SnmpBatterySensorEntity):
    """Representation of a Eaton UPS battery test status sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = None
    _attr_translation_key = "battery_test_status"
    _attr_options = [
        battery_test_status.value for battery_test_status in BatteryTestStatus
    ]

    _name_suffix = "Test Status"
    _value_oid = SNMP_OID_BATTERY_TEST_STATUS


class SnmpInputSensorEntity(SnmpSensorEntity):
    """Representation of a Eaton UPS input sensor."""

    _name_oid = SNMP_OID_INPUT_NAME
    _name_prefix = "Input"


class SnmpInputVoltageSensorEntity(SnmpInputSensorEntity):
    """Representation of a Eaton UPS input voltage sensor."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_registry_visible_default = False

    _name_suffix = "Voltage"
    _value_oid = SNMP_OID_INPUT_VOLTAGE


class SnmpInputCurrentSensorEntity(SnmpInputSensorEntity):
    """Representation of a Eaton UPS input current sensor."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_entity_registry_visible_default = False

    _name_suffix = "Current"
    _value_oid = SNMP_OID_INPUT_CURRENT


class SnmpInputWattsSensorEntity(SnmpInputSensorEntity):
    """Representation of a Eaton UPS input watts sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    _name_suffix = "Watts"
    _value_oid = SNMP_OID_INPUT_WATTS


class SnmpInputSourceSensorEntity(SnmpInputSensorEntity):
    """Representation of a Eaton UPS input source sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_translation_key = "input_source"
    _attr_options = [input_source.value for input_source in InputSource]

    _name_suffix = "Source"
    _value_oid = SNMP_OID_INPUT_SOURCE


class SnmpInputStatusSensorEntity(SnmpInputSensorEntity):
    """Representation of a Eaton UPS input status sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_translation_key = "input_status"
    _attr_options = [input_status.value for input_status in InputStatus]

    _name_suffix = "Status"
    _value_oid = SNMP_OID_INPUT_STATUS


class SnmpOutputSensorEntity(SnmpSensorEntity):
    """Representation of a Eaton UPS output sensor."""

    _name_oid = SNMP_OID_OUTPUT_NAME
    _name_prefix = "Output"


class SnmpOutputVoltageSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output voltage sensor."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_registry_visible_default = False

    _name_suffix = "Voltage"
    _value_oid = SNMP_OID_OUTPUT_VOLTAGE


class SnmpOutputCurrentSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output current sensor."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_entity_registry_visible_default = False

    _name_suffix = "Current"
    _value_oid = SNMP_OID_OUTPUT_CURRENT


class SnmpOutputWattsSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output watts sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    _name_suffix = "Watts"
    _value_oid = SNMP_OID_OUTPUT_WATTS


class SnmpOutputLoadSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output watts sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE

    _name_suffix = "Load"
    _value_oid = SNMP_OID_OUTPUT_LOAD


class SnmpOutputSourceSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output source sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_translation_key = "output_source"
    _attr_options = [output_source.value for output_source in OutputSource]

    _name_suffix = "Source"
    _value_oid = SNMP_OID_OUTPUT_SOURCE


class SnmpOutputStatusSensorEntity(SnmpOutputSensorEntity):
    """Representation of a Eaton UPS output status sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_translation_key = "output_status"
    _attr_options = [output_status.value for output_status in OutputStatus]

    _name_suffix = "Status"
    _value_oid = SNMP_OID_OUTPUT_STATUS
