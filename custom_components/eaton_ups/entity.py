"""Definition of base Eaton UPS Entity"""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.const import (
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
)

from .const import (
    DOMAIN,
    MANUFACTURER,
    SNMP_OID_IDENT_FIRMWARE_VERSION,
    SNMP_OID_IDENT_PART_NUMBER,
    SNMP_OID_IDENT_PRODUCT_NAME,
    SNMP_OID_IDENT_SERIAL_NUMBER,
    SNMP_OID_BATTERY_CAPACITY,
    SNMP_OID_BATTERY_ABM_STATUS,
)

from .coordinator import SnmpCoordinator


class SnmpEntity(CoordinatorEntity[SnmpCoordinator]):
    """Base class for Eaton UPS entities."""

    _name_oid: str | None = None
    _value_oid: str | None = None

    _name_prefix: str = ""
    _name_suffix: str = ""

    def __init__(self, coordinator: SnmpCoordinator, index: str = "") -> None:
        """Initialize a Eaton UPS entity."""
        super().__init__(coordinator)

        device_name = self.device_info["name"]
        if self._name_oid is not None and index != "":
            self._name_oid = self._name_oid.replace("index", str(index))
            sensor_name = self.coordinator.data.get(self._name_oid)
            self._attr_name = (
                f"{device_name} {self._name_prefix} {sensor_name} {self._name_suffix}"
            )
        else:
            self._attr_name = f"{device_name} {self._name_prefix} {self._name_suffix}"

        serial_number = self.coordinator.data.get(SNMP_OID_IDENT_SERIAL_NUMBER)
        self._value_oid = self._value_oid.replace("index", str(index))
        self._attr_unique_id = f"{DOMAIN}_{serial_number}_{self._value_oid}"

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.coordinator.data.get(SNMP_OID_IDENT_SERIAL_NUMBER),
                )
            },
            manufacturer=MANUFACTURER,
            model=self.coordinator.data.get(SNMP_OID_IDENT_PART_NUMBER),
            name=self.coordinator.data.get(SNMP_OID_IDENT_PRODUCT_NAME),
            sw_version=self.coordinator.data.get(SNMP_OID_IDENT_FIRMWARE_VERSION),
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL: self.coordinator.data.get(SNMP_OID_BATTERY_CAPACITY)
        }
