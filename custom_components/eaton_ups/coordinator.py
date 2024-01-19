"""Eaton UPS coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SnmpApi
from .const import (
    DOMAIN,
    SNMP_OID_BATTERY_ABM_STATUS,
    SNMP_OID_BATTERY_AGED,
    # SNMP_OID_BATTERY_CURRENT,
    SNMP_OID_BATTERY_CAPACITY,
    SNMP_OID_BATTERY_FAILURE,
    SNMP_OID_BATTERY_LAST_REPLACED,
    SNMP_OID_BATTERY_LOW_CAPACITY,
    SNMP_OID_BATTERY_NOT_PRESENT,
    SNMP_OID_BATTERY_REMAINING,
    SNMP_OID_BATTERY_TEST_STATUS,
    SNMP_OID_BATTERY_VOLTAGE,
    SNMP_OID_IDENT_FIRMWARE_VERSION,
    SNMP_OID_IDENT_PART_NUMBER,
    SNMP_OID_IDENT_PRODUCT_NAME,
    SNMP_OID_IDENT_SERIAL_NUMBER,
    SNMP_OID_INPUT_CURRENT,
    SNMP_OID_INPUT_NAME,
    SNMP_OID_INPUT_NUM_PHASES,
    SNMP_OID_INPUT_PHASE,
    SNMP_OID_INPUT_SOURCE,
    SNMP_OID_INPUT_STATUS,
    SNMP_OID_INPUT_VOLTAGE,
    SNMP_OID_INPUT_WATTS,
    SNMP_OID_OUTPUT_CURRENT,
    SNMP_OID_OUTPUT_LOAD,
    SNMP_OID_OUTPUT_NAME,
    SNMP_OID_OUTPUT_NUM_PHASES,
    SNMP_OID_OUTPUT_PHASE,
    SNMP_OID_OUTPUT_SOURCE,
    SNMP_OID_OUTPUT_STATUS,
    SNMP_OID_OUTPUT_VOLTAGE,
    SNMP_OID_OUTPUT_WATTS,
)

_LOGGER = logging.getLogger(__name__)


class SnmpCoordinator(DataUpdateCoordinator):
    """Data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self._api = SnmpApi(entry)

    def _update_data(self) -> dict:
        """Fetch the latest data from the source."""
        try:
            data = self._api.get(
                [
                    SNMP_OID_IDENT_PRODUCT_NAME,
                    SNMP_OID_IDENT_PART_NUMBER,
                    SNMP_OID_IDENT_SERIAL_NUMBER,
                    SNMP_OID_IDENT_FIRMWARE_VERSION,
                    SNMP_OID_INPUT_NUM_PHASES,
                    SNMP_OID_INPUT_SOURCE,
                    SNMP_OID_INPUT_STATUS,
                    SNMP_OID_OUTPUT_NUM_PHASES,
                    SNMP_OID_OUTPUT_SOURCE,
                    SNMP_OID_OUTPUT_STATUS,
                    SNMP_OID_BATTERY_REMAINING,
                    SNMP_OID_BATTERY_VOLTAGE,
                    # SNMP_OID_BATTERY_CURRENT,
                    SNMP_OID_BATTERY_CAPACITY,
                    SNMP_OID_BATTERY_ABM_STATUS,
                    SNMP_OID_BATTERY_LAST_REPLACED,
                    SNMP_OID_BATTERY_FAILURE,
                    SNMP_OID_BATTERY_NOT_PRESENT,
                    SNMP_OID_BATTERY_AGED,
                    SNMP_OID_BATTERY_LOW_CAPACITY,
                    SNMP_OID_BATTERY_TEST_STATUS,
                ]
            )

            if self.data is None:
                self.data = data
            else:
                self.data.update(data)

            input_count = self.data.get(SNMP_OID_INPUT_NUM_PHASES, 0)
            if input_count > 0:
                for result in self._api.get_bulk(
                    [
                        SNMP_OID_INPUT_PHASE.replace("index", ""),
                        SNMP_OID_INPUT_VOLTAGE.replace("index", ""),
                        SNMP_OID_INPUT_CURRENT.replace("index", ""),
                        SNMP_OID_INPUT_WATTS.replace("index", ""),
                        SNMP_OID_INPUT_NAME.replace("index", ""),
                    ],
                    input_count,
                ):
                    self.data.update(result)

            output_count = self.data.get(SNMP_OID_OUTPUT_NUM_PHASES, 0)
            if output_count > 0:
                for result in self._api.get_bulk(
                    [
                        SNMP_OID_OUTPUT_PHASE.replace("index", ""),
                        SNMP_OID_OUTPUT_VOLTAGE.replace("index", ""),
                        SNMP_OID_OUTPUT_CURRENT.replace("index", ""),
                        SNMP_OID_OUTPUT_WATTS.replace("index", ""),
                        SNMP_OID_OUTPUT_NAME.replace("index", ""),
                        SNMP_OID_OUTPUT_LOAD.replace("index", ""),
                    ],
                    output_count,
                ):
                    self.data.update(result)

            return self.data

        except RuntimeError as err:
            raise UpdateFailed(err) from err

    async def _async_update_data(self) -> dict:
        """Fetch the latest data from the source."""
        return await self.hass.async_add_executor_job(self._update_data)
