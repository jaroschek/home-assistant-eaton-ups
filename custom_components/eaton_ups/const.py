"""Constants for the Eaton UPS integration."""

from __future__ import annotations

from enum import Enum, StrEnum

from homeassistant.const import Platform

DOMAIN = "eaton_ups"

MANUFACTURER = "Eaton"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

ATTR_NAME = "name"
ATTR_HOST = "host"
ATTR_PORT = "port"
ATTR_VERSION = "version"
ATTR_COMMUNITY = "community"
ATTR_USERNAME = "username"
ATTR_AUTH_PROTOCOL = "auth_protocol"
ATTR_AUTH_KEY = "auth_key"
ATTR_PRIV_PROTOCOL = "priv_protocol"
ATTR_PRIV_KEY = "priv_key"


class SnmpVersion(StrEnum):
    """Enum with snmp versions."""

    V1 = "1"
    V3 = "3"


class AuthProtocol(StrEnum):
    """Enum with snmp auth protocol options."""

    NO_AUTH = "no auth"
    SHA = "sha"
    SHA_256 = "sha256"
    SHA_384 = "sha384"
    SHA_512 = "sha512"


class PrivProtocol(StrEnum):
    """Enum with snmp priv protocol options."""

    NO_PRIV = "no priv"
    AES = "aes"
    AES_192 = "aes192"
    AES_256 = "aes256"


SNMP_API_CLIENT = "snmp_api_client"

SNMP_PORT_DEFAULT = 161

SNMP_OID_IDENT_SYSTEM_NAME = "1.3.6.1.2.1.1.1.0"
SNMP_OID_IDENT_PRODUCT_NAME = "1.3.6.1.4.1.534.1.1.2.0"
SNMP_OID_IDENT_PRODUCT_NAME_XUPS = "1.3.6.1.2.1.33.1.1.2.0"
SNMP_OID_IDENT_FIRMWARE_VERSION = "1.3.6.1.4.1.534.1.1.3.0"
SNMP_OID_IDENT_FIRMWARE_VERSION_XUPS = "1.3.6.1.2.1.33.1.1.3.0"
SNMP_OID_IDENT_PART_NUMBER = "1.3.6.1.4.1.534.1.1.5.0"
SNMP_OID_IDENT_SERIAL_NUMBER = "1.3.6.1.4.1.534.1.1.6.0"
SNMP_OID_IDENT_SERIAL_NUMBER_XUPS = "1.3.6.1.2.1.33.1.1.5.0"

SNMP_OID_BATTERY_REMAINING = "1.3.6.1.4.1.534.1.2.1.0"
SNMP_OID_BATTERY_VOLTAGE = "1.3.6.1.4.1.534.1.2.2.0"
SNMP_OID_BATTERY_CURRENT = "1.3.6.1.4.1.534.1.2.3.0"
SNMP_OID_BATTERY_CAPACITY = "1.3.6.1.4.1.534.1.2.4.0"
SNMP_OID_BATTERY_ABM_STATUS = "1.3.6.1.4.1.534.1.2.5.0"
SNMP_OID_BATTERY_LAST_REPLACED = "1.3.6.1.4.1.534.1.2.6.0"
SNMP_OID_BATTERY_FAILURE = "1.3.6.1.4.1.534.1.2.7.0"
SNMP_OID_BATTERY_NOT_PRESENT = "1.3.6.1.4.1.534.1.2.8.0"
SNMP_OID_BATTERY_AGED = "1.3.6.1.4.1.534.1.2.9.0"
SNMP_OID_BATTERY_LOW_CAPACITY = "1.3.6.1.4.1.534.1.2.10.0"
SNMP_OID_BATTERY_TEST_STATUS = "1.3.6.1.4.1.534.1.8.2.0"

SNMP_OID_INPUT_NUM_PHASES = "1.3.6.1.4.1.534.1.3.3.0"
SNMP_OID_INPUT_PHASE = "1.3.6.1.4.1.534.1.3.4.1.1.index"
SNMP_OID_INPUT_VOLTAGE = "1.3.6.1.4.1.534.1.3.4.1.2.index"
SNMP_OID_INPUT_CURRENT = "1.3.6.1.4.1.534.1.3.4.1.3.index"
SNMP_OID_INPUT_WATTS = "1.3.6.1.4.1.534.1.3.4.1.4.index"
SNMP_OID_INPUT_NAME = "1.3.6.1.4.1.534.1.3.4.1.6.index"
SNMP_OID_INPUT_SOURCE = "1.3.6.1.4.1.534.1.3.5.0"
SNMP_OID_INPUT_STATUS = "1.3.6.1.4.1.534.1.3.9.0"

SNMP_OID_OUTPUT_NUM_PHASES = "1.3.6.1.4.1.534.1.4.3.0"
SNMP_OID_OUTPUT_PHASE = "1.3.6.1.4.1.534.1.4.4.1.1.index"
SNMP_OID_OUTPUT_VOLTAGE = "1.3.6.1.4.1.534.1.4.4.1.2.index"
SNMP_OID_OUTPUT_CURRENT = "1.3.6.1.4.1.534.1.4.4.1.3.index"
SNMP_OID_OUTPUT_WATTS = "1.3.6.1.4.1.534.1.4.4.1.4.index"
SNMP_OID_OUTPUT_NAME = "1.3.6.1.4.1.534.1.4.4.1.6.index"
SNMP_OID_OUTPUT_LOAD = "1.3.6.1.4.1.534.1.4.4.1.8.index"
SNMP_OID_OUTPUT_SOURCE = "1.3.6.1.4.1.534.1.4.5.0"
SNMP_OID_OUTPUT_STATUS = "1.3.6.1.4.1.534.1.4.10.0"


class YesNo(Enum):
    """Mapping for yes/no."""

    yes = 1
    no = 2


class AbmStatus(Enum):
    """Values for ABM Status."""

    battery_charging = 1
    battery_discharging = 2
    battery_floating = 3
    battery_resting = 4
    unknown = 5
    battery_disconnected = 6
    battery_under_test = 7
    check_battery = 8


class BatteryTestStatus(Enum):
    """Values for Battery Test Status."""

    unknow = 1
    passed = 2
    failed = 3
    in_progress = 4
    not_supported = 5
    inhibited = 6
    scheduled = 7


class InputSource(Enum):
    """Values for Input Source."""

    other = 1
    none = 2
    primary_utility = 3
    bypass_feed = 4
    secondary_utility = 5
    generator = 6
    flywheel = 7
    fuelcell = 8


class InputStatus(Enum):
    """Values for Inoput Status."""

    unknown = 0
    bad = 1
    good = 2


class OutputSource(Enum):
    """Values for Output Source."""

    other = 1
    none = 2
    normal = 3
    bypass = 4
    battery = 5
    booster = 6
    reducer = 7
    parallel_capacity = 8
    parallel_redundant = 9
    high_efficiency_mode = 10
    maintenance_bypass = 11
    ess_mode = 12


class OutputStatus(Enum):
    """Values for Output Status."""

    unknow = 0
    output_pot_powered = 1
    output_not_protected = 2
    output_protected = 3
    output_powered_no_continuity = 4
