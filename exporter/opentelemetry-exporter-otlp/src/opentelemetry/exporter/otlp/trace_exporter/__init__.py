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
import os
from typing import Optional, Sequence

from grpc import ChannelCredentials

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.otlp.exporter import (
    OTLPExporterMixin,
    _get_resource_data,
    _load_credential_from_file,
    _translate_key_values,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationLibrary
from opentelemetry.proto.trace.v1.trace_pb2 import (
    InstrumentationLibrarySpans,
    ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import Span as CollectorSpan
from opentelemetry.proto.trace.v1.trace_pb2 import Status
from opentelemetry.sdk.trace import Span as SDKSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.status import StatusCode

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[SDKSpan, ExportTraceServiceRequest, SpanExportResult],
):
    # pylint: disable=unsubscriptable-object
    """OTLP span exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        metadata: Metadata to send when exporting
        timeout: Backend request timeout in seconds
    """

    _result = SpanExportResult
    _stub = TraceServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        if insecure is None:
            insecure = Configuration().EXPORTER_OTLP_SPAN_INSECURE

        if (
            not insecure
            and Configuration().EXPORTER_OTLP_SPAN_CERTIFICATE is not None
        ):
            credentials = credentials or _load_credential_from_file(
                Configuration().EXPORTER_OTLP_SPAN_CERTIFICATE
            )

        super().__init__(
            **{
                "endpoint": endpoint
                or Configuration().EXPORTER_OTLP_SPAN_ENDPOINT,
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                or Configuration().EXPORTER_OTLP_SPAN_HEADERS,
                "timeout": timeout
                or Configuration().EXPORTER_OTLP_SPAN_TIMEOUT,
            }
        )

    def _translate_name(self, sdk_span: SDKSpan) -> None:
        self._collector_span_kwargs["name"] = sdk_span.name

    def _translate_start_time(self, sdk_span: SDKSpan) -> None:
        self._collector_span_kwargs[
            "start_time_unix_nano"
        ] = sdk_span.start_time

    def _translate_end_time(self, sdk_span: SDKSpan) -> None:
        self._collector_span_kwargs["end_time_unix_nano"] = sdk_span.end_time

    def _translate_span_id(self, sdk_span: SDKSpan) -> None:
        self._collector_span_kwargs[
            "span_id"
        ] = sdk_span.context.span_id.to_bytes(8, "big")

    def _translate_trace_id(self, sdk_span: SDKSpan) -> None:
        self._collector_span_kwargs[
            "trace_id"
        ] = sdk_span.context.trace_id.to_bytes(16, "big")

    def _translate_parent(self, sdk_span: SDKSpan) -> None:
        if sdk_span.parent is not None:
            self._collector_span_kwargs[
                "parent_span_id"
            ] = sdk_span.parent.span_id.to_bytes(8, "big")

    def _translate_context_trace_state(self, sdk_span: SDKSpan) -> None:
        if sdk_span.context.trace_state is not None:
            self._collector_span_kwargs["trace_state"] = ",".join(
                [
                    "{}={}".format(key, value)
                    for key, value in (sdk_span.context.trace_state.items())
                ]
            )

    def _translate_attributes(self, sdk_span: SDKSpan) -> None:
        if sdk_span.attributes:

            self._collector_span_kwargs["attributes"] = []

            for key, value in sdk_span.attributes.items():

                try:
                    self._collector_span_kwargs["attributes"].append(
                        _translate_key_values(key, value)
                    )
                except Exception as error:  # pylint: disable=broad-except
                    logger.exception(error)

    def _translate_events(self, sdk_span: SDKSpan) -> None:
        if sdk_span.events:
            self._collector_span_kwargs["events"] = []

            for sdk_span_event in sdk_span.events:

                collector_span_event = CollectorSpan.Event(
                    name=sdk_span_event.name,
                    time_unix_nano=sdk_span_event.timestamp,
                )

                for key, value in sdk_span_event.attributes.items():
                    try:
                        collector_span_event.attributes.append(
                            _translate_key_values(key, value)
                        )
                    # pylint: disable=broad-except
                    except Exception as error:
                        logger.exception(error)

                self._collector_span_kwargs["events"].append(
                    collector_span_event
                )

    def _translate_links(self, sdk_span: SDKSpan) -> None:
        if sdk_span.links:
            self._collector_span_kwargs["links"] = []

            for sdk_span_link in sdk_span.links:

                collector_span_link = CollectorSpan.Link(
                    trace_id=(
                        sdk_span_link.context.trace_id.to_bytes(16, "big")
                    ),
                    span_id=(sdk_span_link.context.span_id.to_bytes(8, "big")),
                )

                for key, value in sdk_span_link.attributes.items():
                    try:
                        collector_span_link.attributes.append(
                            _translate_key_values(key, value)
                        )
                    # pylint: disable=broad-except
                    except Exception as error:
                        logger.exception(error)

                self._collector_span_kwargs["links"].append(
                    collector_span_link
                )

    def _translate_status(self, sdk_span: SDKSpan) -> None:
        if sdk_span.status is not None:
            # TODO: Update this when the proto definitions are updated to include UNSET and ERROR
            proto_status_code = Status.STATUS_CODE_OK
            if sdk_span.status.status_code is StatusCode.ERROR:
                proto_status_code = Status.STATUS_CODE_UNKNOWN_ERROR
            self._collector_span_kwargs["status"] = Status(
                code=proto_status_code, message=sdk_span.status.description,
            )

    def _translate_data(
        self, data: Sequence[SDKSpan]
    ) -> ExportTraceServiceRequest:
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_spans = {}

        for sdk_span in data:

            if sdk_span.resource not in (
                sdk_resource_instrumentation_library_spans.keys()
            ):
                if sdk_span.instrumentation_info is not None:
                    instrumentation_library_spans = InstrumentationLibrarySpans(
                        instrumentation_library=InstrumentationLibrary(
                            name=sdk_span.instrumentation_info.name,
                            version=sdk_span.instrumentation_info.version,
                        )
                    )

                else:
                    instrumentation_library_spans = (
                        InstrumentationLibrarySpans()
                    )

                sdk_resource_instrumentation_library_spans[
                    sdk_span.resource
                ] = instrumentation_library_spans

            self._collector_span_kwargs = {}

            self._translate_name(sdk_span)
            self._translate_start_time(sdk_span)
            self._translate_end_time(sdk_span)
            self._translate_span_id(sdk_span)
            self._translate_trace_id(sdk_span)
            self._translate_parent(sdk_span)
            self._translate_context_trace_state(sdk_span)
            self._translate_attributes(sdk_span)
            self._translate_events(sdk_span)
            self._translate_links(sdk_span)
            self._translate_status(sdk_span)

            self._collector_span_kwargs["kind"] = getattr(
                CollectorSpan.SpanKind,
                "SPAN_KIND_{}".format(sdk_span.kind.name),
            )

            sdk_resource_instrumentation_library_spans[
                sdk_span.resource
            ].spans.append(CollectorSpan(**self._collector_span_kwargs))

        return ExportTraceServiceRequest(
            resource_spans=_get_resource_data(
                sdk_resource_instrumentation_library_spans,
                ResourceSpans,
                "spans",
            )
        )

    def export(self, spans: Sequence[SDKSpan]) -> SpanExportResult:
        return self._export(spans)
