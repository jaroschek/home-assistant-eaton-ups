"""API for Eaton UPS."""

from __future__ import annotations

import logging

from pysnmp.error import PySnmpError
import pysnmp.hlapi.asyncio as hlapi
from pysnmp.hlapi.asyncio import SnmpEngine

from homeassistant.config_entries import ConfigEntry

from .const import (
    ATTR_AUTH_KEY,
    ATTR_AUTH_PROTOCOL,
    ATTR_COMMUNITY,
    ATTR_HOST,
    ATTR_PORT,
    ATTR_PRIV_KEY,
    ATTR_PRIV_PROTOCOL,
    ATTR_USERNAME,
    ATTR_VERSION,
    SNMP_PORT_DEFAULT,
    AuthProtocol,
    PrivProtocol,
    SnmpVersion,
)

AUTH_MAP = {
    AuthProtocol.NO_AUTH: hlapi.usmNoAuthProtocol,
    AuthProtocol.SHA: hlapi.usmHMACSHAAuthProtocol,
    AuthProtocol.SHA_256: hlapi.usmHMAC192SHA256AuthProtocol,
    AuthProtocol.SHA_384: hlapi.usmHMAC256SHA384AuthProtocol,
    AuthProtocol.SHA_512: hlapi.usmHMAC384SHA512AuthProtocol,
}

PRIV_MAP = {
    PrivProtocol.NO_PRIV: hlapi.usmNoPrivProtocol,
    PrivProtocol.AES: hlapi.usmAesCfb128Protocol,
    PrivProtocol.AES_192: hlapi.usmAesCfb192Protocol,
    PrivProtocol.AES_256: hlapi.usmAesCfb256Protocol,
}

_LOGGER = logging.getLogger(__name__)


class SnmpApi:
    """Provide an api for Eaton UPS."""

    _credentials: hlapi.CommunityData | hlapi.UsmUserData
    _target: hlapi.UdpTransportTarget | hlapi.Udp6TransportTarget
    _version: str

    def __init__(self, snmpEngine: SnmpEngine) -> None:
        """Init the SnmpApi."""
        self._snmpEngine = snmpEngine

    async def setup(self, entry: ConfigEntry) -> None:
        """Setup the SnmpApi."""
        try:
            self._target = await hlapi.UdpTransportTarget.create(
                (
                    entry.data.get(ATTR_HOST),
                    entry.data.get(ATTR_PORT, SNMP_PORT_DEFAULT),
                ),
                10,
            )
        except PySnmpError:
            try:
                self._target = await hlapi.Udp6TransportTarget.create(
                    (
                        entry.data.get(ATTR_HOST),
                        entry.data.get(ATTR_PORT, SNMP_PORT_DEFAULT),
                    ),
                    10,
                )
            except PySnmpError as err:
                _LOGGER.error("Invalid SNMP host: %s", err)
                return

        self._version = entry.data.get(ATTR_VERSION)
        if self._version == SnmpVersion.V1:
            self._credentials = hlapi.CommunityData(
                entry.data.get(ATTR_COMMUNITY), mpModel=0
            )
        elif self._version == SnmpVersion.V3:
            self._credentials = hlapi.UsmUserData(
                entry.data.get(ATTR_USERNAME),
                entry.data.get(ATTR_AUTH_KEY),
                entry.data.get(ATTR_PRIV_KEY),
                AUTH_MAP.get(entry.data.get(ATTR_AUTH_PROTOCOL, AuthProtocol.NO_AUTH)),
                PRIV_MAP.get(entry.data.get(ATTR_PRIV_PROTOCOL, PrivProtocol.NO_PRIV)),
            )

    @staticmethod
    def construct_object_types(list_of_oids):
        """Prepare desired objects from list of OIDs."""
        object_types = []
        for oid in list_of_oids:
            object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
        return object_types

    async def get(self, oids) -> dict:
        """Get data for given OIDs in a single call."""
        while len(oids):
            _LOGGER.debug("Get OID(s) %s", oids)

            (
                error_indication,
                error_status,
                error_index,
                var_binds,
            ) = await hlapi.get_cmd(
                self._snmpEngine,
                self._credentials,
                self._target,
                hlapi.ContextData(),
                *__class__.construct_object_types(oids),
            )

            if error_index:
                _LOGGER.debug("Remove error index %d", error_index - 1)
                oids.pop(error_index - 1)
                continue

            if error_indication or error_status:
                raise RuntimeError(
                    f"Got SNMP error: {error_indication} {error_status} {error_index}"
                )

            items = {}
            for var_bind in var_binds:
                items[str(var_bind[0])] = __class__.cast(var_bind[1])
            return items

        return {}

    async def get_bulk(
        self,
        oids,
        count,
        start_from=1,
    ) -> list:
        """Get table data for given OIDs with defined rown count."""
        _LOGGER.debug("Get %s bulk OID(s) %s", count, oids)
        result = []
        var_binds = __class__.construct_object_types(oids)
        for _i in range(count):
            (
                error_indication,
                error_status,
                error_index,
                var_bind_table,
            ) = await hlapi.bulk_cmd(
                self._snmpEngine,
                self._credentials,
                self._target,
                hlapi.ContextData(),
                start_from,
                count,
                *var_binds,
            )

            if not error_indication and not error_indication:
                items = {}
                for var_bind in var_bind_table:
                    items[str(var_bind[0])] = __class__.cast(var_bind[1])
                result.append(items)
            else:
                raise RuntimeError(
                    f"Got SNMP error: {error_indication} {error_status} {error_index}"
                )

            var_binds = var_bind_table

        return result

    async def get_bulk_auto(
        self,
        oids,
        count_oid,
        start_from=1,
    ) -> list:
        """Get table data for given OIDs with determined rown count."""
        return await self.get_bulk(
            oids, await self.get([count_oid])[count_oid], start_from
        )

    @staticmethod
    def cast(value):
        """Cast returned value into correct type."""
        try:
            return int(value)
        except (ValueError, TypeError):
            try:
                return float(value)
            except (ValueError, TypeError):
                try:
                    return str(value)
                except (ValueError, TypeError):
                    pass
        return value
