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

from deprecated import deprecated

NET_HOST_NAME = "net.host.name"
"""
Deprecated: Replaced by `server.address`.
"""


NET_HOST_PORT = "net.host.port"
"""
Deprecated: Replaced by `server.port`.
"""


NET_PEER_NAME = "net.peer.name"
"""
Deprecated: Replaced by `server.address` on client spans and `client.address` on server spans.
"""


NET_PEER_PORT = "net.peer.port"
"""
Deprecated: Replaced by `server.port` on client spans and `client.port` on server spans.
"""


NET_PROTOCOL_NAME = "net.protocol.name"
"""
Deprecated: Replaced by `network.protocol.name`.
"""


NET_PROTOCOL_VERSION = "net.protocol.version"
"""
Deprecated: Replaced by `network.protocol.version`.
"""


NET_SOCK_FAMILY = "net.sock.family"
"""
Deprecated: Split to `network.transport` and `network.type`.
"""


NET_SOCK_HOST_ADDR = "net.sock.host.addr"
"""
Deprecated: Replaced by `network.local.address`.
"""


NET_SOCK_HOST_PORT = "net.sock.host.port"
"""
Deprecated: Replaced by `network.local.port`.
"""


NET_SOCK_PEER_ADDR = "net.sock.peer.addr"
"""
Deprecated: Replaced by `network.peer.address`.
"""


NET_SOCK_PEER_NAME = "net.sock.peer.name"
"""
Deprecated: Removed.
"""


NET_SOCK_PEER_PORT = "net.sock.peer.port"
"""
Deprecated: Replaced by `network.peer.port`.
"""


NET_TRANSPORT = "net.transport"
"""
Deprecated: Replaced by `network.transport`.
"""


@deprecated(
    reason="The attribute net.sock.family is deprecated - Split to `network.transport` and `network.type`"
)
class NetSockFamilyValues(Enum):
    INET = "inet"
    """IPv4 address."""
    INET6 = "inet6"
    """IPv6 address."""
    UNIX = "unix"
    """Unix domain socket path."""


@deprecated(
    reason="The attribute net.transport is deprecated - Replaced by `network.transport`"
)
class NetTransportValues(Enum):
    IP_TCP = "ip_tcp"
    """ip_tcp."""
    IP_UDP = "ip_udp"
    """ip_udp."""
    PIPE = "pipe"
    """Named or anonymous pipe."""
    INPROC = "inproc"
    """In-process communication."""
    OTHER = "other"
    """Something else (non IP-based)."""
