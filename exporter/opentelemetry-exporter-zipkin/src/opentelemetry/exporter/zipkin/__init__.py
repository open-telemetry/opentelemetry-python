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
This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Usage
-----

The **OpenTelemetry Zipkin Exporter** allows exporting of `OpenTelemetry`_
traces to `Zipkin`_. This exporter sends traces to the configured Zipkin
collector endpoint using HTTP and supports multiple protocols (v1 json,
v2 json, v2 protobuf).

.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/sdk-environment-variables.md#zipkin-exporter

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter import zipkin
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinExporter
    zipkin_exporter = zipkin.ZipkinExporter(
        # protocol=Protocol.V2_PROTOBUF
        # optional:
        # endpoint="http://localhost:9411/api/v2/spans",
        # local_node_ipv4="192.168.0.1",
        # local_node_ipv6="2001:db8::c001",
        # local_node_port=31313,
        # max_tag_value_length=256
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The exporter supports the following environment variable for configuration:

- :envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT`

API
---
"""

import logging
from os import environ
from typing import Optional, Sequence

import requests

from opentelemetry.exporter.zipkin.encoder import Encoder, Protocol
from opentelemetry.exporter.zipkin.encoder.v1.json import JsonV1Encoder
from opentelemetry.exporter.zipkin.encoder.v2.json import JsonV2Encoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.node_endpoint import IpInput, NodeEndpoint
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_ZIPKIN_ENDPOINT,
)
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

DEFAULT_ENDPOINT = "http://localhost:9411/api/v2/spans"
REQUESTS_SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class ZipkinExporter(SpanExporter):
    def __init__(
        self,
        protocol: Protocol,
        endpoint: Optional[str] = None,
        local_node_ipv4: IpInput = None,
        local_node_ipv6: IpInput = None,
        local_node_port: Optional[int] = None,
        max_tag_value_length: Optional[int] = None,
    ):
        self.local_node = NodeEndpoint(
            local_node_ipv4, local_node_ipv6, local_node_port
        )

        if endpoint is None:
            endpoint = (
                environ.get(OTEL_EXPORTER_ZIPKIN_ENDPOINT) or DEFAULT_ENDPOINT
            )
        self.endpoint = endpoint

        if protocol == Protocol.V1_JSON:
            self.encoder = JsonV1Encoder(max_tag_value_length)
        elif protocol == Protocol.V2_JSON:
            self.encoder = JsonV2Encoder(max_tag_value_length)
        elif protocol == Protocol.V2_PROTOBUF:
            self.encoder = ProtobufEncoder(max_tag_value_length)

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        result = requests.post(
            url=self.endpoint,
            data=self.encoder.serialize(spans, self.local_node),
            headers={"Content-Type": self.encoder.content_type()},
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
        pass
