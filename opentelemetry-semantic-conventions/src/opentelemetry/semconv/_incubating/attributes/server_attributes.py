# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Final

SERVER_ADDRESS: Final = "server.address"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.server_attributes.SERVER_ADDRESS`.
"""

SERVER_AS_NUMBER: Final = "server.as.number"
"""
The [Autonomous System Number (ASN)](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml) associated with the server IP address.
Note: This attribute SHOULD only be set when the server address is an IP address and the ASN is available from routing, enrichment, or lookup data. The value SHOULD be represented as an integer without the `AS` prefix.
"""

SERVER_AS_ORGANIZATION: Final = "server.as.organization"
"""
The name of the organization associated with the autonomous system of the server IP address.
Note: This attribute SHOULD only be set when `server.as.number` is set and the organization name is available. The value SHOULD be the organization name as provided by the lookup or enrichment source, not the AS name or short code.
"""

SERVER_MAC_ADDRESS: Final = "server.mac.address"
"""
Server Media Access Control (MAC) address.
Note: This attribute MUST identify a MAC address associated with the logical server
endpoint, including when that endpoint is behind intermediaries. If the server's
MAC address is unknown, this attribute MUST NOT be set. The MAC address of a
proxy, gateway, or next-hop router MUST NOT be used as a substitute.

MAC addresses MUST be represented in [IEEE RA hexadecimal form](https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf):
as hyphen-separated octets in uppercase hexadecimal form from most to least significant.

> [!WARNING]
>
> This attribute may contain sensitive (PII) information.
"""

SERVER_PORT: Final = "server.port"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.server_attributes.SERVER_PORT`.
"""

SERVER_PREFIX: Final = "server.prefix"
"""
The IP prefix associated with the server IP address, in CIDR notation.
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

This attribute MUST NOT be set unless `server.address` is set to an IPv4 or
IPv6 address. The address MUST use the same IP version as this prefix and
be contained in it.
"""

SERVER_SERVICE_NAME: Final = "server.service.name"
"""
Logical name of the service acting as the server in a connection-based network interaction.
Note: SHOULD be equal to the actual [`service.name`](/docs/resource/README.md#service) resource attribute of the logical server, if any. This identifies the server service whether the telemetry is recorded by the client, the server, or another observer.
"""

SERVER_SERVICE_NAMESPACE: Final = "server.service.namespace"
"""
Logical namespace of the service acting as the server in a connection-based network interaction.
Note: SHOULD be equal to the actual [`service.namespace`](/docs/resource/README.md#service) resource attribute of the logical server, if any. This identifies the server service's namespace whether the telemetry is recorded by the client, the server, or another observer. Together with `server.service.name`, this identifies the server service. An empty namespace is equivalent to an unspecified namespace.
"""
