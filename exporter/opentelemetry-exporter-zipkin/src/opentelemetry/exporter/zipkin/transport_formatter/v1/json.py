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

"""Zipkin Export Transport Formatter for v1 JSON API

API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin-api.yaml

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
            url="http://localhost:9411/api/v1/spans",
            # optional:
            # ipv4="",
            # ipv6="",
        ),
        transport_format=zipkin.TransportFormat.V1_JSON
        # optional:
        # retry=False,
        # max_tag_value_length=128
    )
"""

import json
from typing import Sequence

from opentelemetry.exporter.zipkin.transport_formatter import (
    TransportFormatter,
)
from opentelemetry.trace import Span, SpanContext


class V1JsonTransportFormatter(TransportFormatter):
    """Zipkin Export Transport Formatter for v1 JSON API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin-api.yaml
    """

    @staticmethod
    def http_content_type() -> str:
        return "application/json"

    def _format(self, spans: Sequence[Span]) -> str:

        formatted_local_endpoint = self._format_local_endpoint()
        zipkin_spans = []

        for span in spans:
            context = span.get_span_context()
            trace_id = context.trace_id
            span_id = context.span_id

            start_timestamp_mus = self.nsec_to_usec_round(span.start_time)
            duration_mus = self.nsec_to_usec_round(
                span.end_time - span.start_time
            )

            annotations = self._extract_annotations_from_events(span.events)

            if annotations is not None:
                for annotation in annotations:
                    annotation["endpoint"] = formatted_local_endpoint

            binary_annotations = self._extract_binary_annotations(
                span, formatted_local_endpoint
            )

            zipkin_span = {
                # Ensure left-zero-padding of traceId, spanId, parentId
                "traceId": format(trace_id, "032x"),
                "id": format(span_id, "016x"),
                "name": span.name,
                "timestamp": start_timestamp_mus,
                "duration": duration_mus,
                "annotations": annotations,
                "binaryAnnotations": binary_annotations,
            }

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

    def _format_local_endpoint(self):
        formatted_local_endpoint = {
            "serviceName": self.local_endpoint.service_name,
            "port": self.local_endpoint.port,
        }

        if self.local_endpoint.ipv4 is not None:
            formatted_local_endpoint["ipv4"] = self.local_endpoint.ipv4

        if self.local_endpoint.ipv6 is not None:
            formatted_local_endpoint["ipv6"] = self.local_endpoint.ipv6

        return formatted_local_endpoint

    def _extract_binary_annotations(
        self, span: Span, formatted_local_endpoint
    ):
        binary_annotations = []

        for k, v in self._extract_tags_from_span(span).items():
            binary_annotations.append(
                {"key": k, "value": v, "endpoint": formatted_local_endpoint}
            )

        if span.instrumentation_info is not None:
            binary_annotations.extend(
                [
                    {
                        "key": "otel.instrumentation_library.name",
                        "value": span.instrumentation_info.name,
                        "endpoint": formatted_local_endpoint,
                    },
                    {
                        "key": "otel.instrumentation_library.version",
                        "value": span.instrumentation_info.version,
                        "endpoint": formatted_local_endpoint,
                    },
                ]
            )

        if span.status is not None:
            binary_annotations.append(
                {
                    "key": "otel.status_code",
                    "value": str(span.status.status_code.value),
                    "endpoint": formatted_local_endpoint,
                }
            )

            if span.status.description is not None:
                binary_annotations.append(
                    {
                        "key": "otel.status_description",
                        "value": span.status.description,
                        "endpoint": formatted_local_endpoint,
                    }
                )

        return binary_annotations
