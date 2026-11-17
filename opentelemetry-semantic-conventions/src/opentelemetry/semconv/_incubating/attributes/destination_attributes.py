# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Final

DESTINATION_ADDRESS: Final = "destination.address"
"""
Destination address as observed at the point of instrumentation - typically an IP address, or a UNIX domain socket name; a domain name only when the receiver was addressed by name (for example a peer-to-peer node dialed by hostname), never obtained via reverse DNS lookup.
Note: `destination.address` SHOULD be the receiver address as observed at the point of instrumentation, for example the destination of the packet, flow, or exchange seen on the wire or socket. Instrumentation SHOULD capture the available address and SHOULD NOT try to resolve the address behind intermediaries such as proxies or load balancers, or perform a reverse DNS lookup to obtain a domain name.
"""

DESTINATION_AS_NUMBER: Final = "destination.as.number"
"""
The [Autonomous System Number (ASN)](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml) associated with the destination IP address.
Note: This attribute SHOULD only be set when the destination address is an IP address and the ASN is available from routing, enrichment, or lookup data. The value SHOULD be represented as an integer without the `AS` prefix.
"""

DESTINATION_AS_ORGANIZATION: Final = "destination.as.organization"
"""
The name of the organization associated with the autonomous system of the destination IP address.
Note: This attribute SHOULD only be set when `destination.as.number` is set and the organization name is available. The value SHOULD be the organization name as provided by the lookup or enrichment source, not the AS name or short code.
"""

DESTINATION_MAC_ADDRESS: Final = "destination.mac.address"
"""
Destination Media Access Control (MAC) address.
Note: MAC addresses MUST be represented in [IEEE RA hexadecimal form](https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf):
as hyphen-separated octets in uppercase hexadecimal form from most to least significant.

> [!WARNING]
>
> This attribute may contain sensitive (PII) information.
"""

DESTINATION_PORT: Final = "destination.port"
"""
Destination port number.
"""

DESTINATION_PREFIX: Final = "destination.prefix"
"""
The IP prefix associated with the destination IP address, in CIDR notation.
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

This attribute MAY be set whether or not `destination.address` is set. If
`destination.address` is also set to an IP address, it MUST use the same IP version
and be contained in this prefix.
"""
