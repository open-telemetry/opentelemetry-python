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
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinSpanExporter
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        service_name="my-helloworld-service",
        # optional:
        # url="http://localhost:9411/api/v2/spans",
        # ipv4="",
        # ipv6="",
        # retry=False,
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

import json
import logging
from typing import Optional, Sequence, Union
from urllib.parse import urlparse

import requests

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin.gen import zipkin_pb2
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span, SpanContext, SpanKind

TRANSPORT_FORMAT_JSON = "json"
TRANSPORT_FORMAT_PROTOBUF = "protobuf"

DEFAULT_RETRY = False
DEFAULT_URL = "http://localhost:9411/api/v2/spans"
DEFAULT_MAX_TAG_VALUE_LENGTH = 128

SPAN_KIND_MAP_JSON = {
    SpanKind.INTERNAL: None,
    SpanKind.SERVER: "SERVER",
    SpanKind.CLIENT: "CLIENT",
    SpanKind.PRODUCER: "PRODUCER",
    SpanKind.CONSUMER: "CONSUMER",
}

SPAN_KIND_MAP_PROTOBUF = {
    SpanKind.INTERNAL: zipkin_pb2.Span.Kind.SPAN_KIND_UNSPECIFIED,
    SpanKind.SERVER: zipkin_pb2.Span.Kind.SERVER,
    SpanKind.CLIENT: zipkin_pb2.Span.Kind.CLIENT,
    SpanKind.PRODUCER: zipkin_pb2.Span.Kind.PRODUCER,
    SpanKind.CONSUMER: zipkin_pb2.Span.Kind.CONSUMER,
}

SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class ZipkinSpanExporter(SpanExporter):
    """Zipkin span exporter for OpenTelemetry.

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        url: The Zipkin endpoint URL
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
        retry: Set to True to configure the exporter to retry on failure.
        transport_format: transport interchange format to use
    """

    def __init__(
        self,
        service_name: str,
        url: str = None,
        ipv4: Optional[str] = None,
        ipv6: Optional[str] = None,
        retry: Optional[str] = DEFAULT_RETRY,
        max_tag_value_length: Optional[int] = DEFAULT_MAX_TAG_VALUE_LENGTH,
        transport_format: Union[
            TRANSPORT_FORMAT_JSON, TRANSPORT_FORMAT_PROTOBUF, None
        ] = None,
    ):
        self.service_name = service_name
        if url is None:
            self.url = Configuration().EXPORTER_ZIPKIN_ENDPOINT or DEFAULT_URL
        else:
            self.url = url

        self.port = urlparse(self.url).port

        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.retry = retry
        self.max_tag_value_length = max_tag_value_length

        if transport_format is None:
            self.transport_format = (
                Configuration().EXPORTER_ZIPKIN_TRANSPORT_FORMAT
                or TRANSPORT_FORMAT_JSON
            )
        else:
            self.transport_format = transport_format

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        if self.transport_format == TRANSPORT_FORMAT_JSON:
            content_type = "application/json"
        elif self.transport_format == TRANSPORT_FORMAT_PROTOBUF:
            content_type = "application/x-protobuf"
        else:
            logger.error("Invalid transport format %s", self.transport_format)
            return SpanExportResult.FAILURE

        result = requests.post(
            url=self.url,
            data=self._translate_to_transport_format(spans),
            headers={"Content-Type": content_type},
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

    def _translate_to_transport_format(self, spans: Sequence[Span]):
        return (
            self._translate_to_json(spans)
            if self.transport_format == TRANSPORT_FORMAT_JSON
            else self._translate_to_protobuf(spans)
        )

    def _translate_to_json(self, spans: Sequence[Span]):
        local_endpoint = {"serviceName": self.service_name, "port": self.port}

        if self.ipv4 is not None:
            local_endpoint["ipv4"] = self.ipv4

        if self.ipv6 is not None:
            local_endpoint["ipv6"] = self.ipv6

        zipkin_spans = []
        for span in spans:
            context = span.get_span_context()
            trace_id = context.trace_id
            span_id = context.span_id

            # Timestamp in zipkin spans is int of microseconds.
            # see: https://zipkin.io/pages/instrumenting.html
            start_timestamp_mus = nsec_to_usec_round(span.start_time)
            duration_mus = nsec_to_usec_round(span.end_time - span.start_time)

            zipkin_span = {
                # Ensure left-zero-padding of traceId, spanId, parentId
                "traceId": format(trace_id, "032x"),
                "id": format(span_id, "016x"),
                "name": span.name,
                "timestamp": start_timestamp_mus,
                "duration": duration_mus,
                "localEndpoint": local_endpoint,
                "kind": SPAN_KIND_MAP_JSON[span.kind],
                "tags": self._extract_tags_from_span(span),
                "annotations": self._extract_annotations_from_events(
                    span.events
                ),
            }

            if span.instrumentation_info is not None:
                zipkin_span["tags"][
                    "otel.instrumentation_library.name"
                ] = span.instrumentation_info.name
                zipkin_span["tags"][
                    "otel.instrumentation_library.version"
                ] = span.instrumentation_info.version

            if span.status is not None:
                zipkin_span["tags"]["otel.status_code"] = str(
                    span.status.status_code.value
                )
                if span.status.description is not None:
                    zipkin_span["tags"][
                        "otel.status_description"
                    ] = span.status.description

            if context.trace_flags.sampled:
                zipkin_span["debug"] = True

            if isinstance(span.parent, Span):
                zipkin_span["parentId"] = format(
                    span.parent.get_span_context().span_id, "016x"
                )
            elif isinstance(span.parent, SpanContext):
                zipkin_span["parentId"] = format(span.parent.span_id, "016x")

            zipkin_spans.append(zipkin_span)

        return json.dumps(zipkin_spans)

    def _translate_to_protobuf(self, spans: Sequence[Span]):

        local_endpoint = zipkin_pb2.Endpoint(
            service_name=self.service_name, port=self.port
        )

        if self.ipv4 is not None:
            local_endpoint.ipv4 = self.ipv4

        if self.ipv6 is not None:
            local_endpoint.ipv6 = self.ipv6

        pbuf_spans = zipkin_pb2.ListOfSpans()

        for span in spans:
            context = span.get_span_context()
            trace_id = context.trace_id.to_bytes(
                length=16, byteorder="big", signed=False,
            )
            span_id = self.format_pbuf_span_id(context.span_id)

            # Timestamp in zipkin spans is int of microseconds.
            # see: https://zipkin.io/pages/instrumenting.html
            start_timestamp_mus = nsec_to_usec_round(span.start_time)
            duration_mus = nsec_to_usec_round(span.end_time - span.start_time)

            # pylint: disable=no-member
            pbuf_span = zipkin_pb2.Span(
                trace_id=trace_id,
                id=span_id,
                name=span.name,
                timestamp=start_timestamp_mus,
                duration=duration_mus,
                local_endpoint=local_endpoint,
                kind=SPAN_KIND_MAP_PROTOBUF[span.kind],
                tags=self._extract_tags_from_span(span),
            )

            annotations = self._extract_annotations_from_events(span.events)

            if annotations is not None:
                for annotation in annotations:
                    pbuf_span.annotations.append(
                        zipkin_pb2.Annotation(
                            timestamp=annotation["timestamp"],
                            value=annotation["value"],
                        )
                    )

            if span.instrumentation_info is not None:
                pbuf_span.tags.update(
                    {
                        "otel.instrumentation_library.name": span.instrumentation_info.name,
                        "otel.instrumentation_library.version": span.instrumentation_info.version,
                    }
                )

            if span.status is not None:
                pbuf_span.tags.update(
                    {"otel.status_code": str(span.status.status_code.value)}
                )
                if span.status.description is not None:
                    pbuf_span.tags.update(
                        {"otel.status_description": span.status.description}
                    )

            if context.trace_flags.sampled:
                pbuf_span.debug = True

            if isinstance(span.parent, Span):
                pbuf_span.parent_id = self.format_pbuf_span_id(
                    span.parent.get_span_context().span_id
                )
            elif isinstance(span.parent, SpanContext):
                pbuf_span.parent_id = self.format_pbuf_span_id(
                    span.parent.span_id
                )

            pbuf_spans.spans.append(pbuf_span)

        return pbuf_spans.SerializeToString()

    @staticmethod
    def format_pbuf_span_id(span_id: int):
        return span_id.to_bytes(length=8, byteorder="big", signed=False)

    def _extract_tags_from_dict(self, tags_dict):
        tags = {}
        if not tags_dict:
            return tags
        for attribute_key, attribute_value in tags_dict.items():
            if isinstance(attribute_value, (int, bool, float)):
                value = str(attribute_value)
            elif isinstance(attribute_value, str):
                value = attribute_value
            else:
                logger.warning("Could not serialize tag %s", attribute_key)
                continue

            if self.max_tag_value_length > 0:
                value = value[: self.max_tag_value_length]
            tags[attribute_key] = value
        return tags

    def _extract_tags_from_span(self, span: Span):
        tags = self._extract_tags_from_dict(getattr(span, "attributes", None))
        if span.resource:
            tags.update(self._extract_tags_from_dict(span.resource.attributes))
        return tags

    def _extract_annotations_from_events(self, events):
        if not events:
            return None

        annotations = []
        for event in events:
            attrs = {}
            for key, value in event.attributes.items():
                if isinstance(value, str):
                    value = value[: self.max_tag_value_length]
                attrs[key] = value

            annotations.append(
                {
                    "timestamp": nsec_to_usec_round(event.timestamp),
                    "value": json.dumps({event.name: attrs}),
                }
            )
        return annotations


def nsec_to_usec_round(nsec):
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10 ** 3
