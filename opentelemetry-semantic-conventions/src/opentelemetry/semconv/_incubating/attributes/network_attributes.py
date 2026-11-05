# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

from typing_extensions import deprecated

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

NETWORK_CONNECTION_STATE: Final = "network.connection.state"
"""
The state of network connection.
Note: Connection states are defined as part of the [rfc9293](https://datatracker.ietf.org/doc/html/rfc9293#section-3.3.2).
"""

NETWORK_CONNECTION_SUBTYPE: Final = "network.connection.subtype"
"""
This describes more details regarding the connection.type. It may be the type of cell technology connection, but it could be used for describing details about a Wi-Fi connection.
"""

NETWORK_CONNECTION_TYPE: Final = "network.connection.type"
"""
The internet connection type.
"""

NETWORK_INTERFACE_NAME: Final = "network.interface.name"
"""
The network interface name.
"""

NETWORK_IO_DIRECTION: Final = "network.io.direction"
"""
The direction of traffic from the perspective of the observing host's physical or virtual network interface. It should not be used to represent the logical direction of a stateful connection or network flow.
"""

NETWORK_LOCAL_ADDRESS: Final = "network.local.address"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_LOCAL_ADDRESS`.
"""

NETWORK_LOCAL_AS_NUMBER: Final = "network.local.as.number"
"""
The [Autonomous System Number (ASN)](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml) associated with the local IP address.
Note: This attribute SHOULD only be set when the local address is an IP address and the ASN is available from routing, enrichment, or lookup data. The value SHOULD be represented as an integer without the `AS` prefix.
"""

NETWORK_LOCAL_AS_ORGANIZATION: Final = "network.local.as.organization"
"""
The name of the organization associated with the autonomous system of the local IP address.
Note: This attribute SHOULD only be set when `network.local.as.number` is set and the organization name is available. The value SHOULD be the organization name as provided by the lookup or enrichment source, not the AS name or short code.
"""

NETWORK_LOCAL_MAC_ADDRESS: Final = "network.local.mac.address"
"""
Local Media Access Control (MAC) address of the network connection.
Note: MAC addresses MUST be represented in [IEEE RA hexadecimal form](https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf):
as hyphen-separated octets in uppercase hexadecimal form from most to least significant.

> [!WARNING]
>
> This attribute may contain sensitive (PII) information.
"""

NETWORK_LOCAL_PORT: Final = "network.local.port"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_LOCAL_PORT`.
"""

NETWORK_LOCAL_PREFIX: Final = "network.local.prefix"
"""
The IP prefix associated with the local IP address, in CIDR notation.
Note: > [!WARNING]
>
> This attribute may contain sensitive (PII) information. A `/32` IPv4 prefix
> or `/128` IPv6 prefix preserves the complete endpoint IP address.
> Using CIDR notation does not guarantee that the data is anonymous.

The value MUST be an IPv4 or IPv6 network prefix in CIDR notation, as defined in
[RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html) for IPv4 and
[RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html#section-2.3) for IPv6.
IPv4 prefixes MUST use a dotted-decimal address followed by `/` and a decimal
prefix length from 0 to 32. IPv6 prefixes MUST use the canonical address text
representation defined in [RFC 5952](https://www.rfc-editor.org/rfc/rfc5952.html),
followed by `/` and a decimal prefix length from 0 to 128. All host bits in
the address MUST be set to zero. The value MUST NOT contain a domain name,
UNIX domain socket name, or IPv6 zone identifier.

Instrumentation or Collector receivers that populate this attribute MUST
convert native representations, such as an address and subnet mask or an
address and prefix length, to equivalent CIDR notation before emitting it.

This attribute MAY be set whether or not `network.local.address` is set. If
`network.local.address` is also set to an IP address, it MUST use the same IP version
and be contained in this prefix.
"""

NETWORK_PEER_ADDRESS: Final = "network.peer.address"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PEER_ADDRESS`.
"""

NETWORK_PEER_AS_NUMBER: Final = "network.peer.as.number"
"""
The [Autonomous System Number (ASN)](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml) associated with the peer IP address.
Note: This attribute SHOULD only be set when the peer address is an IP address and the ASN is available from routing, enrichment, or lookup data. The value SHOULD be represented as an integer without the `AS` prefix.
"""

NETWORK_PEER_AS_ORGANIZATION: Final = "network.peer.as.organization"
"""
The name of the organization associated with the autonomous system of the peer IP address.
Note: This attribute SHOULD only be set when `network.peer.as.number` is set and the organization name is available. The value SHOULD be the organization name as provided by the lookup or enrichment source, not the AS name or short code.
"""

NETWORK_PEER_MAC_ADDRESS: Final = "network.peer.mac.address"
"""
Peer Media Access Control (MAC) address of the network connection.
Note: MAC addresses MUST be represented in [IEEE RA hexadecimal form](https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf):
as hyphen-separated octets in uppercase hexadecimal form from most to least significant.

> [!WARNING]
>
> This attribute may contain sensitive (PII) information.
"""

NETWORK_PEER_PORT: Final = "network.peer.port"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NETWORK_PEER_PORT`.
"""

NETWORK_PEER_PREFIX: Final = "network.peer.prefix"
"""
The IP prefix associated with the peer IP address, in CIDR notation.
Note: > [!WARNING]
>
> This attribute may contain sensitive (PII) information. A `/32` IPv4 prefix
> or `/128` IPv6 prefix preserves the complete endpoint IP address.
> Using CIDR notation does not guarantee that the data is anonymous.

The value MUST be an IPv4 or IPv6 network prefix in CIDR notation, as defined in
[RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html) for IPv4 and
[RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html#section-2.3) for IPv6.
IPv4 prefixes MUST use a dotted-decimal address followed by `/` and a decimal
prefix length from 0 to 32. IPv6 prefixes MUST use the canonical address text
representation defined in [RFC 5952](https://www.rfc-editor.org/rfc/rfc5952.html),
followed by `/` and a decimal prefix length from 0 to 128. All host bits in
the address MUST be set to zero. The value MUST NOT contain a domain name,
UNIX domain socket name, or IPv6 zone identifier.

Instrumentation or Collector receivers that populate this attribute MUST
convert native representations, such as an address and subnet mask or an
address and prefix length, to equivalent CIDR notation before emitting it.

This attribute MAY be set whether or not `network.peer.address` is set. If
`network.peer.address` is also set to an IP address, it MUST use the same IP version
and be contained in this prefix.
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


class NetworkConnectionStateValues(Enum):
    CLOSED = "closed"
    """closed."""
    CLOSE_WAIT = "close_wait"
    """close_wait."""
    CLOSING = "closing"
    """closing."""
    ESTABLISHED = "established"
    """established."""
    FIN_WAIT_1 = "fin_wait_1"
    """fin_wait_1."""
    FIN_WAIT_2 = "fin_wait_2"
    """fin_wait_2."""
    LAST_ACK = "last_ack"
    """last_ack."""
    LISTEN = "listen"
    """listen."""
    SYN_RECEIVED = "syn_received"
    """syn_received."""
    SYN_SENT = "syn_sent"
    """syn_sent."""
    TIME_WAIT = "time_wait"
    """time_wait."""


class NetworkConnectionSubtypeValues(Enum):
    GPRS = "gprs"
    """GPRS."""
    EDGE = "edge"
    """EDGE."""
    UMTS = "umts"
    """UMTS."""
    CDMA = "cdma"
    """CDMA."""
    EVDO_0 = "evdo_0"
    """EVDO Rel. 0."""
    EVDO_A = "evdo_a"
    """EVDO Rev. A."""
    CDMA2000_1XRTT = "cdma2000_1xrtt"
    """CDMA2000 1XRTT."""
    HSDPA = "hsdpa"
    """HSDPA."""
    HSUPA = "hsupa"
    """HSUPA."""
    HSPA = "hspa"
    """HSPA."""
    IDEN = "iden"
    """IDEN."""
    EVDO_B = "evdo_b"
    """EVDO Rev. B."""
    LTE = "lte"
    """LTE."""
    EHRPD = "ehrpd"
    """EHRPD."""
    HSPAP = "hspap"
    """HSPAP."""
    GSM = "gsm"
    """GSM."""
    TD_SCDMA = "td_scdma"
    """TD-SCDMA."""
    IWLAN = "iwlan"
    """IWLAN."""
    NR = "nr"
    """5G NR (New Radio)."""
    NRNSA = "nrnsa"
    """5G NRNSA (New Radio Non-Standalone)."""
    LTE_CA = "lte_ca"
    """LTE CA."""


class NetworkConnectionTypeValues(Enum):
    WIFI = "wifi"
    """Wi-Fi."""
    WIRED = "wired"
    """wired."""
    CELL = "cell"
    """cell."""
    UNAVAILABLE = "unavailable"
    """unavailable."""
    UNKNOWN = "unknown"
    """unknown."""


class NetworkIoDirectionValues(Enum):
    TRANSMIT = "transmit"
    """transmit."""
    RECEIVE = "receive"
    """receive."""


@deprecated(
    "Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues`."
)
class NetworkTransportValues(Enum):
    TCP = "tcp"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues.TCP`."""
    UDP = "udp"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues.UDP`."""
    PIPE = "pipe"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues.PIPE`."""
    UNIX = "unix"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues.UNIX`."""
    QUIC = "quic"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTransportValues.QUIC`."""


@deprecated(
    "Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTypeValues`."
)
class NetworkTypeValues(Enum):
    IPV4 = "ipv4"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTypeValues.IPV4`."""
    IPV6 = "ipv6"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.network_attributes.NetworkTypeValues.IPV6`."""
