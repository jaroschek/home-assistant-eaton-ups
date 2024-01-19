"""The Eaton UPS integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api import SnmpApi
from .const import (
    DOMAIN,
    PLATFORMS,
    SNMP_OID_IDENT_PRODUCT_NAME,
    SNMP_OID_IDENT_SERIAL_NUMBER,
)
from .coordinator import SnmpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Eaton UPS."""
    hass.data[DOMAIN] = {}

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eaton UPS from a config entry."""
    coordinator = SnmpCoordinator(hass=hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        api = SnmpApi(entry.data)
        result = api.get([SNMP_OID_IDENT_PRODUCT_NAME, SNMP_OID_IDENT_SERIAL_NUMBER])

        hass.config_entries.async_update_entry(
            entry,
            unique_id=result.get(SNMP_OID_IDENT_SERIAL_NUMBER),
            title=result.get(SNMP_OID_IDENT_PRODUCT_NAME),
        )

        entry.version = 2

    _LOGGER.info("Migration to version %s successful", entry.version)

    return True
