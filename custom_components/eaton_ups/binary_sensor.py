"""Support for Eaton UPS binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SNMP_OID_BATTERY_AGED,
    SNMP_OID_BATTERY_FAILURE,
    SNMP_OID_BATTERY_LOW_CAPACITY,
    SNMP_OID_BATTERY_NOT_PRESENT,
)
from .coordinator import SnmpCoordinator
from .entity import SnmpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""

    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        SnmpBatteryFailureSensorEntity(coordinator),
        SnmpBatteryNotPresentSensorEntity(coordinator),
        SnmpBatteryAgedSensorEntity(coordinator),
        SnmpBatteryLowCapacitySensorEntity(coordinator),
    ]

    async_add_entities(entities)


class SnmpBinarySensorEntity(SnmpEntity, BinarySensorEntity):
    """Representation of a Eaton UPS battery binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SnmpCoordinator, index: str = "") -> None:
        """Initialize a Eaton UPS sensor."""
        super().__init__(coordinator, index)
        self._attr_native_value = self.coordinator.data.get(self._value_oid)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.get(self._value_oid)

        super().async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return bool(self._attr_native_value == 1)


class SnmpBatteryBinarySensorEntity(SnmpBinarySensorEntity):
    """Representation of a Eaton UPS battery binary sensor."""

    _name_prefix = "Battery"


class SnmpBatteryFailureSensorEntity(SnmpBatteryBinarySensorEntity):
    """Representation of a Eaton UPS battery failure sensor."""

    _name_suffix = "Failure"
    _value_oid = SNMP_OID_BATTERY_FAILURE


class SnmpBatteryNotPresentSensorEntity(SnmpBatteryBinarySensorEntity):
    """Representation of a Eaton UPS battery not present sensor."""

    _name_suffix = "Not Present"
    _value_oid = SNMP_OID_BATTERY_NOT_PRESENT


class SnmpBatteryAgedSensorEntity(SnmpBatteryBinarySensorEntity):
    """Representation of a Eaton UPS battery aged sensor."""

    _name_suffix = "Aged"
    _value_oid = SNMP_OID_BATTERY_AGED


class SnmpBatteryLowCapacitySensorEntity(SnmpBatteryBinarySensorEntity):
    """Representation of a Eaton UPS battery low capacity sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    _name_suffix = "Low Capacity"
    _value_oid = SNMP_OID_BATTERY_LOW_CAPACITY
