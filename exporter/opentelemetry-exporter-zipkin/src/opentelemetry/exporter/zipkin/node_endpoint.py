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

"""Zipkin Exporter Endpoints"""

import ipaddress
from typing import Optional, Union

IpInput = Union[str, int, None]


class NodeEndpoint:
    """The network context of a node in the service graph.

    Args:
        service_name: Lower-case label of this node in the service graph,
          such as "favstar". None if unknown. This is a primary label for
          trace lookup and aggregation, so it should be intuitive and
          consistent. Many use a name from service discovery.
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
        port: Depending on context, this could be a listen port or the
          client-side of a socket. None if unknown.
    """

    def __init__(
        self,
        service_name: str,  # technically optional but enforcing best practice
        ipv4: IpInput = None,
        ipv6: IpInput = None,
        port: Optional[int] = None,
    ):
        self.service_name = service_name
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.port = port

    @property
    def ipv4(self) -> Optional[ipaddress.IPv4Address]:
        return self._ipv4

    @ipv4.setter
    def ipv4(self, address: IpInput) -> None:
        if address is None:
            self._ipv4 = None
        else:
            ipv4_address = ipaddress.ip_address(address)
            if not isinstance(ipv4_address, ipaddress.IPv4Address):
                raise ValueError(
                    "%r does not appear to be an IPv4 address" % address
                )
            self._ipv4 = ipv4_address

    @property
    def ipv6(self) -> Optional[ipaddress.IPv6Address]:
        return self._ipv6

    @ipv6.setter
    def ipv6(self, address: IpInput) -> None:
        if address is None:
            self._ipv6 = None
        else:
            ipv6_address = ipaddress.ip_address(address)
            if not isinstance(ipv6_address, ipaddress.IPv6Address):
                raise ValueError(
                    "%r does not appear to be an IPv6 address" % address
                )
            self._ipv6 = ipv6_address
