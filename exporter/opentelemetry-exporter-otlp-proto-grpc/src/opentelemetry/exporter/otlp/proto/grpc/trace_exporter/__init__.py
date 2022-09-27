# Copyright The OpenTelemetry Authors
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

"""OTLP Span Exporter"""

import logging
from os import environ
from typing import Optional, Sequence

from grpc import ChannelCredentials, Compression

from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    _get_credentials,
    _translate_key_values,
    environ_to_compression,
    get_resource_data,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ScopeSpans,
    ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import Span as CollectorSpan
from opentelemetry.proto.trace.v1.trace_pb2 import Status
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_INSECURE,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[
        ReadableSpan, ExportTraceServiceRequest, SpanExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP span exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: gRPC compression method to use
    """

    _result = SpanExportResult
    _stub = TraceServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):

        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_TRACES_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE
            )

        environ_timeout = environ.get(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
        environ_timeout = (
            int(environ_timeout) if environ_timeout is not None else None
        )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
            if compression is None
            else compression
        )

        super().__init__(
            **{
                "endpoint": endpoint
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT),
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_HEADERS),
                "timeout": timeout or environ_timeout,
                "compression": compression,
            }
        )

    def _translate_name(self, sdk_span: ReadableSpan) -> None:
        self._collector_kwargs["name"] = sdk_span.name

    def _translate_start_time(self, sdk_span: ReadableSpan) -> None:
        self._collector_kwargs["start_time_unix_nano"] = sdk_span.start_time

    def _translate_end_time(self, sdk_span: ReadableSpan) -> None:
        self._collector_kwargs["end_time_unix_nano"] = sdk_span.end_time

    def _translate_span_id(self, sdk_span: ReadableSpan) -> None:
        self._collector_kwargs["span_id"] = sdk_span.context.span_id.to_bytes(
            8, "big"
        )

    def _translate_trace_id(self, sdk_span: ReadableSpan) -> None:
        self._collector_kwargs[
            "trace_id"
        ] = sdk_span.context.trace_id.to_bytes(16, "big")

    def _translate_parent(self, sdk_span: ReadableSpan) -> None:
        if sdk_span.parent is not None:
            self._collector_kwargs[
                "parent_span_id"
            ] = sdk_span.parent.span_id.to_bytes(8, "big")

    def _translate_context_trace_state(self, sdk_span: ReadableSpan) -> None:
        if sdk_span.context.trace_state is not None:
            self._collector_kwargs["trace_state"] = ",".join(
                [
                    f"{key}={value}"
                    for key, value in (sdk_span.context.trace_state.items())
                ]
            )

    def _translate_events(self, sdk_span: ReadableSpan) -> None:
        if sdk_span.events:
            self._collector_kwargs["events"] = []

            for sdk_span_event in sdk_span.events:

                collector_span_event = CollectorSpan.Event(
                    name=sdk_span_event.name,
                    time_unix_nano=sdk_span_event.timestamp,
                    dropped_attributes_count=sdk_span_event.attributes.dropped,
                )

                for key, value in sdk_span_event.attributes.items():
                    try:
                        collector_span_event.attributes.append(
                            _translate_key_values(key, value)
                        )
                    # pylint: disable=broad-except
                    except Exception as error:
                        logger.exception(error)

                self._collector_kwargs["events"].append(collector_span_event)

    def _translate_links(self, sdk_span: ReadableSpan) -> None:
        if sdk_span.links:
            self._collector_kwargs["links"] = []

            for sdk_span_link in sdk_span.links:

                collector_span_link = CollectorSpan.Link(
                    trace_id=(
                        sdk_span_link.context.trace_id.to_bytes(16, "big")
                    ),
                    span_id=(sdk_span_link.context.span_id.to_bytes(8, "big")),
                    dropped_attributes_count=sdk_span_link.attributes.dropped,
                )

                for key, value in sdk_span_link.attributes.items():
                    try:
                        collector_span_link.attributes.append(
                            _translate_key_values(key, value)
                        )
                    # pylint: disable=broad-except
                    except Exception as error:
                        logger.exception(error)

                self._collector_kwargs["links"].append(collector_span_link)

    def _translate_status(self, sdk_span: ReadableSpan) -> None:
        # pylint: disable=no-member
        if sdk_span.status is not None:
            self._collector_kwargs["status"] = Status(
                code=sdk_span.status.status_code.value,
                message=sdk_span.status.description,
            )

    def _translate_data(
        self, data: Sequence[ReadableSpan]
    ) -> ExportTraceServiceRequest:
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_scope_spans = {}

        for sdk_span in data:
            scope_spans_map = sdk_resource_scope_spans.get(
                sdk_span.resource, {}
            )
            # If we haven't seen the Resource yet, add it to the map
            if not scope_spans_map:
                sdk_resource_scope_spans[sdk_span.resource] = scope_spans_map
            scope_spans = scope_spans_map.get(sdk_span.instrumentation_scope)
            # If we haven't seen the InstrumentationScope for this Resource yet, add it to the map
            if not scope_spans:
                if sdk_span.instrumentation_scope is not None:
                    scope_spans_map[
                        sdk_span.instrumentation_scope
                    ] = ScopeSpans(
                        scope=InstrumentationScope(
                            name=sdk_span.instrumentation_scope.name,
                            version=sdk_span.instrumentation_scope.version,
                        )
                    )
                else:
                    # If no InstrumentationScope, store in None key
                    scope_spans_map[
                        sdk_span.instrumentation_scope
                    ] = ScopeSpans()
            scope_spans = scope_spans_map.get(sdk_span.instrumentation_scope)
            self._collector_kwargs = {}

            self._translate_name(sdk_span)
            self._translate_start_time(sdk_span)
            self._translate_end_time(sdk_span)
            self._translate_span_id(sdk_span)
            self._translate_trace_id(sdk_span)
            self._translate_parent(sdk_span)
            self._translate_context_trace_state(sdk_span)
            self._collector_kwargs["attributes"] = self._translate_attributes(
                sdk_span.attributes
            )
            self._translate_events(sdk_span)
            self._translate_links(sdk_span)
            self._translate_status(sdk_span)
            if sdk_span.dropped_attributes:
                self._collector_kwargs[
                    "dropped_attributes_count"
                ] = sdk_span.dropped_attributes
            if sdk_span.dropped_events:
                self._collector_kwargs[
                    "dropped_events_count"
                ] = sdk_span.dropped_events
            if sdk_span.dropped_links:
                self._collector_kwargs[
                    "dropped_links_count"
                ] = sdk_span.dropped_links

            self._collector_kwargs["kind"] = getattr(
                CollectorSpan.SpanKind,
                f"SPAN_KIND_{sdk_span.kind.name}",
            )

            scope_spans.spans.append(CollectorSpan(**self._collector_kwargs))

        return ExportTraceServiceRequest(
            resource_spans=get_resource_data(
                sdk_resource_scope_spans,
                ResourceSpans,
                "spans",
            )
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._export(spans)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    @property
    def _exporting(self):
        return "traces"
