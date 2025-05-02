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

"""
OpenTelemetry Zipkin JSON Exporter
----------------------------------

This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Usage
-----

The **OpenTelemetry Zipkin JSON Exporter** allows exporting of `OpenTelemetry`_
traces to `Zipkin`_. This exporter sends traces to the configured Zipkin
collector endpoint using JSON over HTTP and supports multiple versions (v1, v2).

.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/sdk-environment-variables.md#zipkin-exporter

.. code:: python

    import requests

    from opentelemetry import trace
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinExporter
    zipkin_exporter = ZipkinExporter(
        # version=Protocol.V2
        # optional:
        # endpoint="http://localhost:9411/api/v2/spans",
        # local_node_ipv4="192.168.0.1",
        # local_node_ipv6="2001:db8::c001",
        # local_node_port=31313,
        # max_tag_value_length=256,
        # timeout=5 (in seconds),
        # session=requests.Session(),
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The exporter supports the following environment variable for configuration:

- :envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT`
- :envvar:`OTEL_EXPORTER_ZIPKIN_TIMEOUT`

API
---
"""

import logging
from os import environ
from typing import Optional, Sequence

import requests

from opentelemetry.exporter.zipkin.encoder import Protocol
from opentelemetry.exporter.zipkin.json.v1 import JsonV1Encoder
from opentelemetry.exporter.zipkin.json.v2 import JsonV2Encoder
from opentelemetry.exporter.zipkin.node_endpoint import IpInput, NodeEndpoint
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_ZIPKIN_ENDPOINT,
    OTEL_EXPORTER_ZIPKIN_TIMEOUT,
)
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

DEFAULT_ENDPOINT = "http://localhost:9411/api/v2/spans"
REQUESTS_SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class ZipkinExporter(SpanExporter):
    def __init__(
        self,
        version: Protocol = Protocol.V2,
        endpoint: Optional[str] = None,
        local_node_ipv4: IpInput = None,
        local_node_ipv6: IpInput = None,
        local_node_port: Optional[int] = None,
        max_tag_value_length: Optional[int] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """Zipkin exporter.

        Args:
            version: The protocol version to be used.
            endpoint: The endpoint of the Zipkin collector.
            local_node_ipv4: Primary IPv4 address associated with this connection.
            local_node_ipv6: Primary IPv6 address associated with this connection.
            local_node_port: Depending on context, this could be a listen port or the
                client-side of a socket.
            max_tag_value_length: Max length string attribute values can have.
            timeout: Maximum time the Zipkin exporter will wait for each batch export.
                The default value is 10s.
            session: Connection session to the Zipkin collector endpoint.

            The tuple (local_node_ipv4, local_node_ipv6, local_node_port) is used to represent
            the network context of a node in the service graph.
        """
        self.local_node = NodeEndpoint(
            local_node_ipv4, local_node_ipv6, local_node_port
        )

        if endpoint is None:
            endpoint = (
                environ.get(OTEL_EXPORTER_ZIPKIN_ENDPOINT) or DEFAULT_ENDPOINT
            )
        self.endpoint = endpoint

        if version == Protocol.V1:
            self.encoder = JsonV1Encoder(max_tag_value_length)
        elif version == Protocol.V2:
            self.encoder = JsonV2Encoder(max_tag_value_length)

        self.session = session or requests.Session()
        self.session.headers.update(
            {"Content-Type": self.encoder.content_type()}
        )
        self._closed = False
        self.timeout = timeout or int(
            environ.get(OTEL_EXPORTER_ZIPKIN_TIMEOUT, 10)
        )

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        # Populate service_name from first span
        # We restrict any SpanProcessor to be only associated with a single
        # TracerProvider, so it is safe to assume that all Spans in a single
        # batch all originate from one TracerProvider (and in turn have all
        # the same service.name)
        if spans:
            service_name = spans[0].resource.attributes.get(SERVICE_NAME)
            if service_name:
                self.local_node.service_name = service_name
        result = self.session.post(
            url=self.endpoint,
            data=self.encoder.serialize(spans, self.local_node),
            timeout=self.timeout,
        )

        if result.status_code not in REQUESTS_SUCCESS_STATUS_CODES:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        if self._closed:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self.session.close()
        self._closed = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
