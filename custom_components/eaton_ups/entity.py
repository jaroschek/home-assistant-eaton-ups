"""Definition of base Eaton UPS Entity."""

from __future__ import annotations

from homeassistant.const import ATTR_BATTERY_LEVEL
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_HOST,
    DOMAIN,
    MANUFACTURER,
    SNMP_OID_BATTERY_CAPACITY,
    SNMP_OID_IDENT_FIRMWARE_VERSION,
    SNMP_OID_IDENT_FIRMWARE_VERSION_XUPS,
    SNMP_OID_IDENT_PART_NUMBER,
    SNMP_OID_IDENT_PRODUCT_NAME,
    SNMP_OID_IDENT_PRODUCT_NAME_XUPS,
    SNMP_OID_IDENT_SERIAL_NUMBER,
    SNMP_OID_IDENT_SERIAL_NUMBER_XUPS,
    SNMP_OID_IDENT_SYSTEM_NAME,
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

        self._value_oid = self._value_oid.replace("index", str(index))
        self._attr_unique_id = f"{DOMAIN}_{self.identifier}_{self._value_oid}"

    @property
    def identifier(self):
        """Return the device identifier."""
        return self.coordinator.data.get(
            SNMP_OID_IDENT_SERIAL_NUMBER,
            self.coordinator.data.get(
                SNMP_OID_IDENT_SERIAL_NUMBER_XUPS,
                self.coordinator.config_entry.data.get(ATTR_HOST),
            ),
        )

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.identifier)},
            manufacturer=MANUFACTURER,
            model=self.coordinator.data.get(SNMP_OID_IDENT_PART_NUMBER),
            name=self.coordinator.data.get(
                SNMP_OID_IDENT_SYSTEM_NAME,
                self.coordinator.data.get(
                    SNMP_OID_IDENT_PRODUCT_NAME,
                    self.coordinator.data.get(SNMP_OID_IDENT_PRODUCT_NAME_XUPS),
                ),
            ),
            serial_number=self.coordinator.data.get(
                SNMP_OID_IDENT_SERIAL_NUMBER,
                self.coordinator.data.get(SNMP_OID_IDENT_SERIAL_NUMBER_XUPS),
            ),
            sw_version=self.coordinator.data.get(
                SNMP_OID_IDENT_FIRMWARE_VERSION,
                self.coordinator.data.get(SNMP_OID_IDENT_FIRMWARE_VERSION_XUPS),
            ),
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL: self.coordinator.data.get(SNMP_OID_BATTERY_CAPACITY)
        }
