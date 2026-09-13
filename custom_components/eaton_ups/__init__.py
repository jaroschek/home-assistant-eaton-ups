"""The Eaton UPS integration."""

from __future__ import annotations

from pysnmp.hlapi.asyncio import SnmpEngine

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .api import SnmpApi
from .const import PLATFORMS
from .coordinator import SnmpCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eaton UPS from a config entry."""
    snmp_engine = await hass.async_add_executor_job(SnmpEngine)
    api = SnmpApi(snmp_engine)
    await api.setup(entry)
    coordinator = SnmpCoordinator(hass=hass, api=api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True
