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
This library allows to export tracing data to an OTLP collector.

Usage
-----

The **OTLP Span Exporter** allows to export `OpenTelemetry`_ traces to the
`OTLP`_ collector.

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. envvar:: OTEL_EXPORTER_OTLP_CERTIFICATE
.. envvar:: OTEL_EXPORTER_OTLP_COMPRESSION
.. envvar:: OTEL_EXPORTER_OTLP_ENDPOINT
.. envvar:: OTEL_EXPORTER_OTLP_HEADERS
.. envvar:: OTEL_EXPORTER_OTLP_INSECURE
.. envvar:: OTEL_EXPORTER_OTLP_TIMEOUT

Additional details on the environment variables are available in the
`specification<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md#opentelemetry-protocol-exporter>`.

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp import OTLPSpanExporter
    from opentelemetry.exporter.otlp.util import Protocol
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    otlp_exporter = OTLPSpanExporter(protocol=Protocol.GRPC)

    span_processor = BatchExportSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

API
---
"""

import logging
from os import environ
from typing import Dict, Optional, Sequence

from opentelemetry.exporter.otlp.encoder.protobuf import ProtobufEncoder
from opentelemetry.exporter.otlp.sender.grpc import GrpcSender
from opentelemetry.exporter.otlp.sender.http import HttpSender
from opentelemetry.exporter.otlp.util import (
    Compression,
    Headers,
    HeadersInput,
    Protocol,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)

DEFAULT_COMPRESSION = Compression.NONE
DEFAULT_ENDPOINT = "https://localhost:4317"
DEFAULT_INSECURE = False
DEFAULT_TIMEOUT = 10  # seconds


class OTLPSpanExporter(SpanExporter):
    """OTLP span exporter

    Args:
        protocol: transport protocol (e.g. grpc)
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: secure or insecure endpoint connection
        certificate_file: TLS credential file path for secure connection
        headers: Headers to send when exporting
        compression: Compression algorithm to be used in channel
        timeout: Backend request timeout in seconds
    """

    def __init__(
        self,
        protocol: Protocol,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        endpoint = (
            endpoint
            or environ.get(OTEL_EXPORTER_OTLP_ENDPOINT)
            or DEFAULT_ENDPOINT
        )

        if insecure is None:
            insecure = bool(
                environ.get(OTEL_EXPORTER_OTLP_INSECURE) or DEFAULT_INSECURE
            )

        if insecure:
            certificate_file = None
        else:
            certificate_file = certificate_file or environ.get(
                OTEL_EXPORTER_OTLP_CERTIFICATE
            )

        headers = _parse_headers(
            headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        )

        timeout = (
            timeout
            or int(environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, 0))
            or DEFAULT_TIMEOUT
        )

        if compression is None:
            compression_env_val = environ.get(OTEL_EXPORTER_OTLP_COMPRESSION)
            if compression_env_val is not None:
                compression = Compression(compression_env_val)
            else:
                compression = Compression.NONE

        if protocol == Protocol.GRPC:
            self._sender = GrpcSender(
                endpoint,
                insecure,
                certificate_file,
                headers,
                timeout,
                compression,
            )
        else:
            self._sender = HttpSender(
                endpoint,
                insecure,
                certificate_file,
                headers,
                timeout,
                compression,
            )

        self._encoder = ProtobufEncoder()

    def export(self, sdk_spans: Sequence[Span]) -> SpanExportResult:
        if isinstance(self._sender, GrpcSender):
            send_result = self._sender.send(self._encoder.encode(sdk_spans))
        else:
            send_result = self._sender.send(  # pylint: disable=too-many-function-args
                self._encoder.serialize(sdk_spans),
                self._encoder.content_type(),
            )

        if send_result:
            export_result = SpanExportResult.SUCCESS
        else:
            export_result = SpanExportResult.FAILURE

        return export_result

    def shutdown(self) -> None:
        pass


def _parse_headers(headers_input: HeadersInput) -> Optional[Headers]:
    if isinstance(headers_input, dict):
        headers = headers_input
    elif isinstance(headers_input, str):
        headers = {}
        for header in headers_input.split(","):
            header_parts = header.split("=")
            if len(header_parts) == 2:
                headers[header_parts[0]] = header_parts[1]
            else:
                logger.warning(
                    "Skipped invalid OTLP exporter header: %r", header
                )
        if not headers:
            headers = None
    else:
        headers = None

    return headers
