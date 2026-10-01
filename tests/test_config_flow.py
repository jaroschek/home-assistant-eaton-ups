"""Tests for settings changes and automatic reloads."""

from unittest.mock import patch

import pytest

from custom_components.eaton_ups.config_flow import OptionsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.mark.parametrize(
    ("version", "credentials"),
    [
        pytest.param("1", {"community": "private"}, id="snmp-v1"),
        pytest.param(
            "3",
            {
                "username": "user",
                "auth_protocol": "no auth",
                "auth_key": "",
                "priv_protocol": "no priv",
                "priv_key": "",
            },
            id="snmp-v3",
        ),
    ],
)
async def test_options_reload(
    hass: HomeAssistant, entry: ConfigEntry, version: str, credentials: dict[str, str]
) -> None:
    """Saving credentials and host settings must reload the running integration."""
    flow = OptionsFlow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    host_input = {"host": "192.0.2.2", "port": 1161, "version": version}
    result = await flow.async_step_host(host_input)
    assert result["step_id"] == f"v{version}"
    result = await getattr(flow, f"async_step_v{version}")(credentials)
    assert result["type"] == FlowResultType.CREATE_ENTRY

    with patch.object(hass.config_entries, "async_schedule_reload") as reload_entry:
        await hass.config_entries.options.async_finish_flow(flow, result)
        reload_entry.assert_called_once_with(entry.entry_id)

    assert entry.data["host"] == "192.0.2.2"
    assert entry.data["port"] == 1161
    assert entry.data["version"] == version
    assert entry.data.items() >= credentials.items()
    assert entry.options == entry.data


async def test_unchanged_options_do_not_reload(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """An unchanged options flow must not schedule a duplicate reload."""
    hass.config_entries.async_update_entry(entry, options=dict(entry.data))
    flow = OptionsFlow(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_v1({"community": "public"})

    with patch.object(hass.config_entries, "async_schedule_reload") as reload_entry:
        await hass.config_entries.options.async_finish_flow(flow, result)
        reload_entry.assert_not_called()
