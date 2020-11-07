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

The **OpenTelemetry Zipkin Exporter** allows to export `OpenTelemetry`_ traces to `Zipkin`_.
This exporter always send traces to the configured Zipkin collector using HTTP.


.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/sdk-environment-variables.md#zipkin-exporter

.. envvar:: OTEL_EXPORTER_ZIPKIN_ENDPOINT
.. envvar:: OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter import zipkin
    from opentelemetry.exporter.zipkin.endpoint import LocalEndpoint
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinSpanExporter
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        LocalEndpoint(
            service_name="my-helloworld-service",
            # optional:
            # url="http://localhost:9411/api/v2/spans",
            # ipv4="",
            # ipv6="",
        ),
        # optional:
        # retry=False,
        # max_tag_value_length=128
        # transport_format=zipkin.TransportFormat.V2_JSON
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The exporter supports the following environment variables for configuration:

:envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT`: target to which the exporter will
send data. This may include a path (e.g. http://example.com:9411/api/v2/spans).

:envvar:`OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT`: transport interchange format
to use when sending data. Currently only Zipkin's v2 json and protobuf formats
are supported, with v2 json being the default.

API
---
"""

from enum import Enum
import logging
from typing import Optional, Sequence

import requests

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin.endpoint import LocalEndpoint
from opentelemetry.exporter.zipkin.transport_formatter.v1.json import (
    V1JsonTransportFormatter,
)
from opentelemetry.exporter.zipkin.transport_formatter.v2.json import (
    V2JsonTransportFormatter,
)
from opentelemetry.exporter.zipkin.transport_formatter.v2.protobuf import (
    V2ProtobufTransportFormatter,
)
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

DEFAULT_RETRY = False

SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class TransportFormat(Enum):
    """Enum of supported transport formats.

    Values are human-readable strings so that the related OS environ var
    OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT can be more easily used.
    """

    V1_JSON = "v1_json"
    V2_JSON = "v2_json"
    V2_PROTOBUF = "v2_protobuf"


class ZipkinSpanExporter(SpanExporter):
    """Zipkin span exporter for OpenTelemetry.

    Args:
        local_endpoint: Zipkin endpoint where exports will be sent
        retry: Set to True to configure the exporter to retry on failure.
        max_tag_value_length: Length limit for exported tag values
        transport_format: transport interchange format to use
    """

    def __init__(
        self,
        local_endpoint: LocalEndpoint,
        retry: Optional[str] = DEFAULT_RETRY,
        max_tag_value_length: Optional[int] = None,
        transport_format: Optional[TransportFormat] = None,
    ):
        self.local_endpoint = local_endpoint
        self.retry = retry
        self.max_tag_value_length = max_tag_value_length

        if transport_format is None:
            env_transport = Configuration().EXPORTER_ZIPKIN_TRANSPORT_FORMAT
            if env_transport is None:
                self.transport_format = TransportFormat.V2_JSON
            else:
                self.transport_format = TransportFormat(env_transport)
        else:
            self.transport_format = transport_format

        if self.transport_format is TransportFormat.V1_JSON:
            self.transport_formatter = V1JsonTransportFormatter(
                self.local_endpoint, self.max_tag_value_length
            )
        elif self.transport_format is TransportFormat.V2_JSON:
            self.transport_formatter = V2JsonTransportFormatter(
                local_endpoint, self.max_tag_value_length
            )
        elif self.transport_format is TransportFormat.V2_PROTOBUF:
            self.transport_formatter = V2ProtobufTransportFormatter(
                local_endpoint, self.max_tag_value_length
            )

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        result = requests.post(
            url=self.local_endpoint.url,
            data=self.transport_formatter.format(spans),
            headers={"Content-Type": self.transport_formatter.http_content_type()},
        )

        if result.status_code not in SUCCESS_STATUS_CODES:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )

            if self.retry:
                return SpanExportResult.FAILURE
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass
