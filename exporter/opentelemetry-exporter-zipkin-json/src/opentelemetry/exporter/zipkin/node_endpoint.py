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

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

IpInput = Union[str, int, None]


class NodeEndpoint:
    """The network context of a node in the service graph.

    Args:
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
        port: Depending on context, this could be a listen port or the
          client-side of a socket. None if unknown.
    """

    def __init__(
        self,
        ipv4: IpInput = None,
        ipv6: IpInput = None,
        port: Optional[int] = None,
    ):
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.port = port

        tracer_provider = trace.get_tracer_provider()

        if hasattr(tracer_provider, "resource"):
            resource = tracer_provider.resource
        else:
            resource = Resource.create()

        self.service_name = resource.attributes[SERVICE_NAME]

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
                    f"{address!r} does not appear to be an IPv4 address"
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
                    f"{address!r} does not appear to be an IPv6 address"
                )
            self._ipv6 = ipv6_address
