"""API for Eaton UPS."""

from __future__ import annotations

from collections.abc import Iterable
import logging

from pyasn1.type.base import Asn1Type
from pysnmp.error import PySnmpError
import pysnmp.hlapi.v3arch.asyncio as hlapi
from pysnmp.hlapi.v3arch.asyncio import SnmpEngine
from pysnmp.proto.rfc1905 import EndOfMibView, NoSuchInstance, NoSuchObject

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
    AuthProtocol.NO_AUTH: hlapi.USM_AUTH_NONE,
    AuthProtocol.MD5: hlapi.USM_AUTH_HMAC96_MD5,
    AuthProtocol.SHA: hlapi.USM_AUTH_HMAC96_SHA,
    AuthProtocol.SHA_224: hlapi.USM_AUTH_HMAC128_SHA224,
    AuthProtocol.SHA_256: hlapi.USM_AUTH_HMAC192_SHA256,
    AuthProtocol.SHA_384: hlapi.USM_AUTH_HMAC256_SHA384,
    AuthProtocol.SHA_512: hlapi.USM_AUTH_HMAC384_SHA512,
}

PRIV_MAP = {
    PrivProtocol.NO_PRIV: hlapi.USM_PRIV_NONE,
    PrivProtocol.AES: hlapi.USM_PRIV_CFB128_AES,
    PrivProtocol.AES_192: hlapi.USM_PRIV_CFB192_AES,
    PrivProtocol.AES_256: hlapi.USM_PRIV_CFB256_AES,
}

SNMP_EXCEPTION_TYPES = (NoSuchObject, NoSuchInstance, EndOfMibView)

_LOGGER = logging.getLogger(__name__)


class SnmpApi:
    """Provide an api for Eaton UPS."""

    _credentials: hlapi.CommunityData | hlapi.UsmUserData
    _target: hlapi.UdpTransportTarget | hlapi.Udp6TransportTarget
    _version: str

    def __init__(self, snmp_engine: SnmpEngine) -> None:
        """Init the SnmpApi."""
        self._snmp_engine = snmp_engine

    async def setup(self, entry: ConfigEntry) -> None:
        """Set up the SNMP transport and credentials."""
        address = (entry.data[ATTR_HOST], entry.data.get(ATTR_PORT, SNMP_PORT_DEFAULT))
        try:
            self._target = await hlapi.UdpTransportTarget.create(address, timeout=10)
        except PySnmpError:
            self._target = await hlapi.Udp6TransportTarget.create(address, timeout=10)

        self._version = entry.data[ATTR_VERSION]
        if self._version == SnmpVersion.V1:
            self._credentials = hlapi.CommunityData(
                entry.data[ATTR_COMMUNITY], mpModel=0
            )
        elif self._version == SnmpVersion.V3:
            self._credentials = hlapi.UsmUserData(
                entry.data[ATTR_USERNAME],
                entry.data.get(ATTR_AUTH_KEY) or None,
                entry.data.get(ATTR_PRIV_KEY) or None,
                AUTH_MAP[entry.data.get(ATTR_AUTH_PROTOCOL, AuthProtocol.NO_AUTH)],
                PRIV_MAP[entry.data.get(ATTR_PRIV_PROTOCOL, PrivProtocol.NO_PRIV)],
            )

    @staticmethod
    def construct_object_types(oids: Iterable[str]) -> list[hlapi.ObjectType]:
        """Prepare desired objects from a list of OIDs."""
        return [hlapi.ObjectType(hlapi.ObjectIdentity(oid.rstrip("."))) for oid in oids]

    async def get(self, oids: Iterable[str]) -> dict[str, int | float | str]:
        """Get data for the given OIDs."""
        remaining_oids = list(oids)
        while remaining_oids:
            _LOGGER.debug("Get OID(s) %s", remaining_oids)
            (
                error_indication,
                error_status,
                error_index,
                var_binds,
            ) = await hlapi.get_cmd(
                self._snmp_engine,
                self._credentials,
                self._target,
                hlapi.ContextData(),
                *self.construct_object_types(remaining_oids),
            )

            if (
                not error_indication
                and error_status == 2
                and 0 < error_index <= len(remaining_oids)
            ):
                # SNMPv1 reports unsupported OIDs using noSuchName.
                _LOGGER.debug(
                    "Skip unsupported OID %s", remaining_oids[error_index - 1]
                )
                remaining_oids.pop(error_index - 1)
                continue

            if error_indication or error_status:
                raise RuntimeError(
                    f"Got SNMP error: {error_indication} {error_status} {error_index}"
                )

            return {
                str(oid): value
                for oid, raw_value in var_binds
                if (value := self.cast(raw_value)) is not None
            }

        return {}

    async def get_bulk(
        self,
        oids: Iterable[str],
        count: int,
        start_from: int = 1,
    ) -> list[dict[str, int | float | str]]:
        """Get the requested number of rows from SNMP table columns."""
        roots = [oid.rstrip(".") for oid in oids]
        _LOGGER.debug("Get %s bulk OID(s) %s", count, roots)
        if count <= 0 or not roots:
            return []

        request_oids = roots
        if start_from > 1:
            request_oids = [f"{root}.{start_from - 1}" for root in roots]

        result = []
        width = len(roots)
        remaining = count
        var_binds = self.construct_object_types(request_oids)
        while remaining:
            (
                error_indication,
                error_status,
                error_index,
                var_bind_table,
            ) = await hlapi.bulk_cmd(
                self._snmp_engine,
                self._credentials,
                self._target,
                hlapi.ContextData(),
                0,
                min(4, remaining),
                *var_binds,
            )

            if error_indication or error_status:
                raise RuntimeError(
                    f"Got SNMP error: {error_indication} {error_status} {error_index}"
                )

            rows = [
                var_bind_table[index : index + width]
                for index in range(0, len(var_bind_table), width)
                if len(var_bind_table[index : index + width]) == width
            ]
            if not rows:
                break

            for row in rows:
                items = {}
                finished = True
                for root, (oid, raw_value) in zip(roots, row, strict=True):
                    oid = str(oid)
                    if not oid.startswith(f"{root}.") or isinstance(
                        raw_value, SNMP_EXCEPTION_TYPES
                    ):
                        continue
                    finished = False
                    if (value := self.cast(raw_value)) is not None:
                        items[oid] = value

                if finished:
                    return result
                result.append(items)
                remaining -= 1
                if not remaining:
                    return result

            var_binds = rows[-1]

        return result

    async def get_bulk_auto(
        self,
        oids: Iterable[str],
        count_oid: str,
        start_from: int = 1,
    ) -> list[dict[str, int | float | str]]:
        """Get table rows using the count reported by the device."""
        data = await self.get([count_oid])
        return await self.get_bulk(oids, int(data.get(count_oid, 0)), start_from)

    @staticmethod
    def cast(value: Asn1Type) -> int | float | str | None:
        """Cast an SNMP value, treating missing readings as unknown."""
        if isinstance(value, SNMP_EXCEPTION_TYPES):
            return None
        try:
            return int(value)
        except ValueError, TypeError:
            try:
                return float(value)
            except ValueError, TypeError:
                return str(value) or None
