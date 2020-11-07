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
from urllib.parse import urlparse

from opentelemetry.configuration import Configuration

DEFAULT_URL = "http://localhost:9411/api/v2/spans"


class LocalEndpoint:
    """Local endpoint information

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        url: The Zipkin endpoint URL
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
    """

    def __init__(
        self,
        service_name: str,
        url: str = None,
        ipv4: Optional[str] = None,
        ipv6: Optional[str] = None,
    ):
        self.service_name = service_name

        if url is None:
            self.url = Configuration().EXPORTER_ZIPKIN_ENDPOINT or DEFAULT_URL
        else:
            self.url = url

        self.port = urlparse(self.url).port

        self.ipv4 = ipv4
        self.ipv6 = ipv6
