# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import Enum
from typing import Final

from deprecated import deprecated

NETWORK_CARRIER_ICC: Final = "network.carrier.icc"
"""
The ISO 3166-1 alpha-2 2-character country code associated with the mobile carrier network.
"""

NETWORK_CARRIER_MCC: Final = "network.carrier.mcc"
"""
The mobile carrier country code.
"""

NETWORK_CARRIER_MNC: Final = "network.carrier.mnc"
"""
The mobile carrier network code.
"""

NETWORK_CARRIER_NAME: Final = "network.carrier.name"
"""
The name of the mobile carrier.
"""

NETWORK_CONNECTION_SUBTYPE: Final = "network.connection.subtype"
"""
This describes more details regarding the connection.type. It may be the type of cell technology connection, but it could be used for describing details about a wifi connection.
"""

NETWORK_CONNECTION_TYPE: Final = "network.connection.type"
"""
The internet connection type.
"""

NETWORK_IO_DIRECTION: Final = "network.io.direction"
"""
The network IO operation direction.
"""

NETWORK_LOCAL_ADDRESS: Final = "network.local.address"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_LOCAL_ADDRESS`.
"""

NETWORK_LOCAL_PORT: Final = "network.local.port"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_LOCAL_PORT`.
"""

NETWORK_PEER_ADDRESS: Final = "network.peer.address"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PEER_ADDRESS`.
"""

NETWORK_PEER_PORT: Final = "network.peer.port"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PEER_PORT`.
"""

NETWORK_PROTOCOL_NAME: Final = "network.protocol.name"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PROTOCOL_NAME`.
"""

NETWORK_PROTOCOL_VERSION: Final = "network.protocol.version"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PROTOCOL_VERSION`.
"""

NETWORK_TRANSPORT: Final = "network.transport"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_TRANSPORT`.
"""

NETWORK_TYPE: Final = "network.type"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_TYPE`.
"""


class NetworkConnectionSubtypeValues(Enum):
    GPRS: Final = "gprs"
    """GPRS."""
    EDGE: Final = "edge"
    """EDGE."""
    UMTS: Final = "umts"
    """UMTS."""
    CDMA: Final = "cdma"
    """CDMA."""
    EVDO_0: Final = "evdo_0"
    """EVDO Rel. 0."""
    EVDO_A: Final = "evdo_a"
    """EVDO Rev. A."""
    CDMA2000_1XRTT: Final = "cdma2000_1xrtt"
    """CDMA2000 1XRTT."""
    HSDPA: Final = "hsdpa"
    """HSDPA."""
    HSUPA: Final = "hsupa"
    """HSUPA."""
    HSPA: Final = "hspa"
    """HSPA."""
    IDEN: Final = "iden"
    """IDEN."""
    EVDO_B: Final = "evdo_b"
    """EVDO Rev. B."""
    LTE: Final = "lte"
    """LTE."""
    EHRPD: Final = "ehrpd"
    """EHRPD."""
    HSPAP: Final = "hspap"
    """HSPAP."""
    GSM: Final = "gsm"
    """GSM."""
    TD_SCDMA: Final = "td_scdma"
    """TD-SCDMA."""
    IWLAN: Final = "iwlan"
    """IWLAN."""
    NR: Final = "nr"
    """5G NR (New Radio)."""
    NRNSA: Final = "nrnsa"
    """5G NRNSA (New Radio Non-Standalone)."""
    LTE_CA: Final = "lte_ca"
    """LTE CA."""


class NetworkConnectionTypeValues(Enum):
    WIFI: Final = "wifi"
    """wifi."""
    WIRED: Final = "wired"
    """wired."""
    CELL: Final = "cell"
    """cell."""
    UNAVAILABLE: Final = "unavailable"
    """unavailable."""
    UNKNOWN: Final = "unknown"
    """unknown."""


class NetworkIoDirectionValues(Enum):
    TRANSMIT: Final = "transmit"
    """transmit."""
    RECEIVE: Final = "receive"
    """receive."""


@deprecated(reason="Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues`.")  # type: ignore
class NetworkTransportValues(Enum):
    TCP: Final = "tcp"
    """TCP."""
    UDP: Final = "udp"
    """UDP."""
    PIPE: Final = "pipe"
    """Named or anonymous pipe."""
    UNIX: Final = "unix"
    """Unix domain socket."""


@deprecated(reason="Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTypeValues`.")  # type: ignore
class NetworkTypeValues(Enum):
    IPV4: Final = "ipv4"
    """IPv4."""
    IPV6: Final = "ipv6"
    """IPv6."""
