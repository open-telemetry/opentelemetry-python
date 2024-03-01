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

# pylint: disable=too-many-lines

from enum import Enum


NET_HOST_NAME = "net.host.name"
"""
Deprecated, use `server.address`.
Deprecated: Replaced by `server.address`.
"""


NET_HOST_PORT = "net.host.port"
"""
Deprecated, use `server.port`.
Deprecated: Replaced by `server.port`.
"""


NET_PEER_NAME = "net.peer.name"
"""
Deprecated, use `server.address` on client spans and `client.address` on server spans.
Deprecated: Replaced by `server.address` on client spans and `client.address` on server spans.
"""


NET_PEER_PORT = "net.peer.port"
"""
Deprecated, use `server.port` on client spans and `client.port` on server spans.
Deprecated: Replaced by `server.port` on client spans and `client.port` on server spans.
"""


NET_PROTOCOL_NAME = "net.protocol.name"
"""
Deprecated, use `network.protocol.name`.
Deprecated: Replaced by `network.protocol.name`.
"""


NET_PROTOCOL_VERSION = "net.protocol.version"
"""
Deprecated, use `network.protocol.version`.
Deprecated: Replaced by `network.protocol.version`.
"""


NET_SOCK_FAMILY = "net.sock.family"
"""
Deprecated, use `network.transport` and `network.type`.
Deprecated: Split to `network.transport` and `network.type`.
"""


NET_SOCK_HOST_ADDR = "net.sock.host.addr"
"""
Deprecated, use `network.local.address`.
Deprecated: Replaced by `network.local.address`.
"""


NET_SOCK_HOST_PORT = "net.sock.host.port"
"""
Deprecated, use `network.local.port`.
Deprecated: Replaced by `network.local.port`.
"""


NET_SOCK_PEER_ADDR = "net.sock.peer.addr"
"""
Deprecated, use `network.peer.address`.
Deprecated: Replaced by `network.peer.address`.
"""


NET_SOCK_PEER_NAME = "net.sock.peer.name"
"""
Deprecated, no replacement at this time.
Deprecated: Removed.
"""


NET_SOCK_PEER_PORT = "net.sock.peer.port"
"""
Deprecated, use `network.peer.port`.
Deprecated: Replaced by `network.peer.port`.
"""


NET_TRANSPORT = "net.transport"
"""
Deprecated, use `network.transport`.
Deprecated: Replaced by `network.transport`.
"""

class NetSockFamilyValues(Enum):
    INET = "inet"
    """IPv4 address."""

    INET6 = "inet6"
    """IPv6 address."""

    UNIX = "unix"
    """Unix domain socket path."""
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
