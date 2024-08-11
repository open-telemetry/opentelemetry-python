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

NET_HOST_NAME: Final = "net.host.name"
"""
Deprecated: Replaced by `server.address`.
"""

NET_HOST_PORT: Final = "net.host.port"
"""
Deprecated: Replaced by `server.port`.
"""

NET_PEER_NAME: Final = "net.peer.name"
"""
Deprecated: Replaced by `server.address` on client spans and `client.address` on server spans.
"""

NET_PEER_PORT: Final = "net.peer.port"
"""
Deprecated: Replaced by `server.port` on client spans and `client.port` on server spans.
"""

NET_PROTOCOL_NAME: Final = "net.protocol.name"
"""
Deprecated: Replaced by `network.protocol.name`.
"""

NET_PROTOCOL_VERSION: Final = "net.protocol.version"
"""
Deprecated: Replaced by `network.protocol.version`.
"""

NET_SOCK_FAMILY: Final = "net.sock.family"
"""
Deprecated: Split to `network.transport` and `network.type`.
"""

NET_SOCK_HOST_ADDR: Final = "net.sock.host.addr"
"""
Deprecated: Replaced by `network.local.address`.
"""

NET_SOCK_HOST_PORT: Final = "net.sock.host.port"
"""
Deprecated: Replaced by `network.local.port`.
"""

NET_SOCK_PEER_ADDR: Final = "net.sock.peer.addr"
"""
Deprecated: Replaced by `network.peer.address`.
"""

NET_SOCK_PEER_NAME: Final = "net.sock.peer.name"
"""
Deprecated: Removed.
"""

NET_SOCK_PEER_PORT: Final = "net.sock.peer.port"
"""
Deprecated: Replaced by `network.peer.port`.
"""

NET_TRANSPORT: Final = "net.transport"
"""
Deprecated: Replaced by `network.transport`.
"""


@deprecated(reason="The attribute net.sock.family is deprecated - Split to `network.transport` and `network.type`")  # type: ignore
class NetSockFamilyValues(Enum):
    INET: Final = "inet"
    """IPv4 address."""
    INET6: Final = "inet6"
    """IPv6 address."""
    UNIX: Final = "unix"
    """Unix domain socket path."""


@deprecated(reason="The attribute net.transport is deprecated - Replaced by `network.transport`")  # type: ignore
class NetTransportValues(Enum):
    IP_TCP: Final = "ip_tcp"
    """ip_tcp."""
    IP_UDP: Final = "ip_udp"
    """ip_udp."""
    PIPE: Final = "pipe"
    """Named or anonymous pipe."""
    INPROC: Final = "inproc"
    """In-process communication."""
    OTHER: Final = "other"
    """Something else (non IP-based)."""
