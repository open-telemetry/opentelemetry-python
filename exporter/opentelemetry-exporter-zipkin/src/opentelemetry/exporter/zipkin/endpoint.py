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

from typing import Optional


class Endpoint:
    """Endpoint definition

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
        service_name: str,
        ipv4: Optional[str] = None,
        ipv6: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.service_name = service_name
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.port = port
