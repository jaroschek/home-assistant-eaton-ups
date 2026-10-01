"""Regression tests for the SNMP reader."""

from unittest.mock import AsyncMock, MagicMock, patch

from pyasn1.type.base import Asn1Type
from pysnmp.error import PySnmpError
from pysnmp.hlapi.v3arch.asyncio import CommunityData, SnmpEngine, UsmUserData
from pysnmp.proto.rfc1902 import Integer, ObjectName, OctetString
from pysnmp.proto.rfc1905 import EndOfMibView, NoSuchInstance, NoSuchObject
import pytest

from custom_components.eaton_ups import api as api_module
from custom_components.eaton_ups.api import SnmpApi
from homeassistant.config_entries import ConfigEntry

COLUMNS = ["1.3.6.1.2.1.33.1.3.3.1.2", "1.3.6.1.2.1.33.1.3.3.1.3"]


@pytest.fixture
def api() -> SnmpApi:
    """Provide an API without opening any network connections."""
    instance = SnmpApi(MagicMock(spec=SnmpEngine))
    instance._credentials = CommunityData("public", mpModel=0)
    instance._target = MagicMock()
    return instance


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(Integer(0), 0, id="zero"),
        pytest.param(Integer(42), 42, id="integer"),
        pytest.param(OctetString("1.25"), 1.25, id="decimal"),
        pytest.param(OctetString("Serial"), "Serial", id="text"),
        pytest.param(OctetString(""), None, id="empty"),
        pytest.param(NoSuchObject(), None, id="no-such-object"),
        pytest.param(NoSuchInstance(), None, id="no-such-instance"),
        pytest.param(EndOfMibView(), None, id="end-of-mib"),
    ],
)
def test_cast(value: Asn1Type, expected: float | str | None) -> None:
    """SNMP exceptions and empty values must not become measurements."""
    assert SnmpApi.cast(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(OctetString(""), id="empty"),
        pytest.param(NoSuchObject(), id="no-such-object"),
        pytest.param(NoSuchInstance(), id="no-such-instance"),
        pytest.param(EndOfMibView(), id="end-of-mib"),
    ],
)
async def test_get_missing(api: SnmpApi, value: Asn1Type) -> None:
    """Keep valid zeros while omitting unavailable readings."""
    reply = (
        None,
        0,
        0,
        [(ObjectName(COLUMNS[0]), value), (ObjectName(COLUMNS[1]), Integer(0))],
    )
    with patch.object(api_module.hlapi, "get_cmd", AsyncMock(return_value=reply)):
        assert await api.get(COLUMNS) == {COLUMNS[1]: 0}


async def test_get_v1_missing_does_not_mutate_oids(api: SnmpApi) -> None:
    """An unsupported SNMPv1 OID must be retried on the next refresh."""
    oids = list(COLUMNS)
    reply = (None, 0, 0, [(ObjectName(COLUMNS[1]), Integer(42))])
    with patch.object(
        api_module.hlapi,
        "get_cmd",
        AsyncMock(side_effect=[(None, 2, 1, []), reply, reply]),
    ) as get_cmd:
        assert await api.get(oids) == {COLUMNS[1]: 42}
        assert oids == COLUMNS
        assert await api.get(oids) == {COLUMNS[1]: 42}
        assert [len(call.args) - 4 for call in get_cmd.await_args_list] == [2, 1, 2]


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(("Timeout", 0, 0, []), id="timeout"),
        pytest.param((None, 6, 1, []), id="no-access"),
        pytest.param((None, 2, 0, []), id="invalid-error-index"),
    ],
)
async def test_get_errors(api: SnmpApi, reply: tuple) -> None:
    """Transport and agent errors must not be silently discarded."""
    with patch.object(
        api_module.hlapi, "get_cmd", AsyncMock(return_value=reply)
    ) as get_cmd:
        with pytest.raises(RuntimeError, match="SNMP error"):
            await api.get(COLUMNS)
        get_cmd.assert_awaited_once()


@pytest.mark.parametrize(
    ("rows_per_response", "credential"),
    [
        pytest.param(1, CommunityData("public", mpModel=0), id="snmp-v1"),
        pytest.param(4, UsmUserData("user"), id="snmp-v3"),
    ],
)
async def test_bulk_fixed_width(
    api: SnmpApi, rows_per_response: int, credential: CommunityData | UsmUserData
) -> None:
    """Read six rows without adding request columns or losing continuation."""
    api._credentials = credential
    rows = [
        [(ObjectName(f"{oid}.{index}"), Integer(index)) for oid in COLUMNS]
        for index in range(1, 7)
    ]
    responses = [
        (
            None,
            0,
            0,
            [item for row in rows[index : index + rows_per_response] for item in row],
        )
        for index in range(0, 6, rows_per_response)
    ]
    with patch.object(
        api_module.hlapi, "bulk_cmd", AsyncMock(side_effect=responses)
    ) as bulk_cmd:
        assert await api.get_bulk([f"{oid}." for oid in COLUMNS], 6) == [
            {f"{oid}.{index}": index for oid in COLUMNS} for index in range(1, 7)
        ]
        calls = bulk_cmd.await_args_list
        assert [len(call.args) - 6 for call in calls] == [2] * len(responses)
        assert [call.args[4] for call in calls] == [0] * len(responses)
        assert [call.args[5] for call in calls] == [
            min(4, 6 - index) for index in range(0, 6, rows_per_response)
        ]
        assert [call.args[6:] for call in calls[1:]] == [
            tuple(rows[index - 1])
            for index in range(rows_per_response, 6, rows_per_response)
        ]


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(("Timeout", 0, 0, []), id="timeout"),
        pytest.param((None, 6, 1, []), id="no-access"),
    ],
)
async def test_bulk_errors(api: SnmpApi, reply: tuple) -> None:
    """Bulk reads must check both transport errors and the agent status."""
    with (
        patch.object(api_module.hlapi, "bulk_cmd", AsyncMock(return_value=reply)),
        pytest.raises(RuntimeError, match="SNMP error"),
    ):
        await api.get_bulk(COLUMNS, 1)


async def test_bulk_stops_at_column_end(api: SnmpApi) -> None:
    """Do not collect values from unrelated columns after a table ends."""
    responses = [
        (
            None,
            0,
            0,
            [
                (ObjectName(f"{COLUMNS[0]}.1"), NoSuchInstance()),
                (ObjectName(f"{COLUMNS[1]}.1"), Integer(0)),
            ],
        ),
        (
            None,
            0,
            0,
            [
                (ObjectName(f"{COLUMNS[1]}.1"), Integer(99)),
                (ObjectName(f"{COLUMNS[1]}.1"), EndOfMibView()),
            ],
        ),
    ]
    with patch.object(
        api_module.hlapi, "bulk_cmd", AsyncMock(side_effect=responses)
    ) as bulk_cmd:
        assert await api.get_bulk(COLUMNS, 6) == [{f"{COLUMNS[1]}.1": 0}]
        assert bulk_cmd.await_count == 2


async def test_bulk_limits_extra_rows(api: SnmpApi) -> None:
    """Return only the requested rows even if a device sends extra rows."""
    reply = (
        None,
        0,
        0,
        [
            (ObjectName(f"{oid}.{index}"), Integer(index))
            for index in range(1, 4)
            for oid in COLUMNS
        ],
    )
    with patch.object(
        api_module.hlapi, "bulk_cmd", AsyncMock(return_value=reply)
    ) as bulk_cmd:
        assert await api.get_bulk(COLUMNS, 1) == [{f"{oid}.1": 1 for oid in COLUMNS}]
        bulk_cmd.assert_awaited_once()


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param([], id="empty"),
        pytest.param(
            [(ObjectName(f"{COLUMNS[0]}.1"), Integer(1))], id="incomplete-row"
        ),
    ],
)
async def test_bulk_empty_reply(api: SnmpApi, reply: list) -> None:
    """A truncated table response must terminate the walk."""
    with patch.object(
        api_module.hlapi, "bulk_cmd", AsyncMock(return_value=(None, 0, 0, reply))
    ):
        assert await api.get_bulk(COLUMNS, 2) == []


@pytest.mark.parametrize(
    ("oids", "count"),
    [pytest.param([], 1, id="no-columns"), pytest.param(COLUMNS, 0, id="no-rows")],
)
async def test_bulk_empty_request(api: SnmpApi, oids: list[str], count: int) -> None:
    """An empty request must not contact the device."""
    with patch.object(api_module.hlapi, "bulk_cmd", AsyncMock()) as bulk_cmd:
        assert await api.get_bulk(oids, count) == []
        bulk_cmd.assert_not_awaited()


async def test_bulk_start_row(api: SnmpApi) -> None:
    """Start GETNEXT immediately before the first requested row."""
    reply = (None, 0, 0, [(ObjectName(f"{oid}.3"), Integer(3)) for oid in COLUMNS])
    with (
        patch.object(api_module.hlapi, "bulk_cmd", AsyncMock(return_value=reply)),
        patch.object(
            api_module.hlapi, "ObjectIdentity", wraps=api_module.hlapi.ObjectIdentity
        ) as identity,
    ):
        assert await api.get_bulk(COLUMNS, 1, start_from=3) == [
            {f"{oid}.3": 3 for oid in COLUMNS}
        ]
        assert [call.args[0] for call in identity.call_args_list] == [
            f"{oid}.2" for oid in COLUMNS
        ]


@pytest.mark.parametrize(
    ("data", "count"),
    [
        pytest.param({"count": 2}, 2, id="known-count"),
        pytest.param({}, 0, id="missing-count"),
    ],
)
async def test_bulk_auto(api: SnmpApi, data: dict[str, int], count: int) -> None:
    """Await the scalar read before looking up the row count."""
    with (
        patch.object(api, "get", AsyncMock(return_value=data)),
        patch.object(api, "get_bulk", AsyncMock(return_value=[])) as get_bulk,
    ):
        assert await api.get_bulk_auto(COLUMNS, "count") == []
        get_bulk.assert_awaited_once_with(COLUMNS, count, 1)


async def test_setup_ipv6_fallback(api: SnmpApi, entry: ConfigEntry) -> None:
    """An IPv6 address must use the IPv6 transport after IPv4 lookup fails."""
    with (
        patch.object(
            api_module.hlapi.UdpTransportTarget,
            "create",
            AsyncMock(side_effect=PySnmpError("IPv4 lookup failed")),
        ),
        patch.object(
            api_module.hlapi.Udp6TransportTarget, "create", AsyncMock()
        ) as create,
    ):
        await api.setup(entry)
        create.assert_awaited_once_with((entry.data["host"], 161), timeout=10)
        assert api._target is create.return_value


async def test_setup_unresolved_host(api: SnmpApi, entry: ConfigEntry) -> None:
    """A failed lookup must raise instead of leaving an uninitialized API."""
    with (
        patch.object(
            api_module.hlapi.UdpTransportTarget,
            "create",
            AsyncMock(side_effect=PySnmpError("IPv4 lookup failed")),
        ),
        patch.object(
            api_module.hlapi.Udp6TransportTarget,
            "create",
            AsyncMock(side_effect=PySnmpError("IPv6 lookup failed")),
        ),
        pytest.raises(PySnmpError, match="IPv6 lookup failed"),
    ):
        await api.setup(entry)
