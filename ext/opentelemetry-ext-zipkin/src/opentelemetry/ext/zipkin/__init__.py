# Copyright 2019, OpenTelemetry Authors
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

"""Zipkin Span Exporter for OpenTelemetry."""

import json
import logging
from typing import Optional, Sequence

import requests

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span, SpanContext, SpanKind

DEFAULT_ENDPOINT = "/api/v2/spans"
DEFAULT_HOST_NAME = "localhost"
DEFAULT_PORT = 9411
DEFAULT_PROTOCOL = "http"
ZIPKIN_HEADERS = {"Content-Type": "application/json"}

SPAN_KIND_MAP = {
    SpanKind.INTERNAL: None,
    SpanKind.SERVER: "SERVER",
    SpanKind.CLIENT: "CLIENT",
    SpanKind.PRODUCER: "PRODUCER",
    SpanKind.CONSUMER: "CONSUMER",
}

SUCCESS_STATUS_CODE = (200, 202)

logger = logging.getLogger(__name__)


class ZipkinSpanExporter(SpanExporter):
    """Zipkin span exporter for OpenTelemetry.

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        host_name: The host name of the Zipkin server
        port: The port of the Zipkin server
        endpoint: The endpoint of the Zipkin server
        protocol: The protocol used for the request.
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
    """

    def __init__(
        self,
        service_name: str,
        host_name: Optional[str] = DEFAULT_HOST_NAME,
        port: Optional[int] = DEFAULT_PORT,
        endpoint: Optional[str] = DEFAULT_ENDPOINT,
        protocol: Optional[str] = DEFAULT_PROTOCOL,
        ipv4: Optional[str] = None,
        ipv6: Optional[str] = None,
    ):
        self.service_name = service_name
        self.host_name = host_name
        self.port = port
        self.endpoint = endpoint
        self.protocol = protocol
        self.url = self.get_url
        self.ipv4 = ipv4
        self.ipv6 = ipv6

    @property
    def get_url(self):
        return "{}://{}:{}{}".format(
            self.protocol, self.host_name, self.port, self.endpoint
        )

    def export(self, spans: Sequence[Span]) -> "SpanExportResult":
        zipkin_spans = self._translate_to_zipkin(spans)
        print("about to call")
        result = requests.post(
            url=self.url, data=json.dumps(zipkin_spans), headers=ZIPKIN_HEADERS
        )

        if result.status_code not in SUCCESS_STATUS_CODE:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )
            # TODO: should we retry here?
            return SpanExportResult.FAILED_NOT_RETRYABLE
        return SpanExportResult.SUCCESS

    def _translate_to_zipkin(self, spans: Sequence[Span]):

        local_endpoint = {
            "serviceName": self.service_name,
            "port": self.port,
        }

        if self.ipv4 is not None:
            local_endpoint["ipv4"] = self.ipv4

        if self.ipv6 is not None:
            local_endpoint["ipv6"] = self.ipv6

        zipkin_spans = []
        for span in spans:
            ctx = span.get_context()
            trace_id = ctx.trace_id
            span_id = ctx.span_id

            # Timestamp in zipkin spans is int of microseconds.
            start_timestamp_mus = _nsec_to_usec_round(span.start_time)
            duration_mus = _nsec_to_usec_round(span.end_time - span.start_time)

            zipkin_span = {
                "traceId": _format(trace_id),
                "id": _format(span_id),
                "name": span.name,
                "timestamp": start_timestamp_mus,
                "duration": duration_mus,
                "localEndpoint": local_endpoint,
                "kind": SPAN_KIND_MAP[span.kind],
                "tags": _extract_tags_from_span(span.attributes),
                "annotations": _extract_annotations_from_events(span.events),
            }

            if isinstance(span.parent, Span):
                zipkin_span["parentId"] = _format(
                    span.parent.get_context().span_id
                )
            elif isinstance(span.parent, SpanContext):
                zipkin_span["parentId"] = _format(span.parent.span_id)

            zipkin_spans.append(zipkin_span)
        return zipkin_spans

    def shutdown(self) -> None:
        pass


def _format(unformatted_id):
    return format(unformatted_id, "x")


def _extract_tags_from_span(attr):
    if not attr:
        return None
    tags = {}
    for attribute_key, attribute_value in attr.items():
        if isinstance(attribute_value, (int, bool, float)):
            value = str(attribute_value)
        elif isinstance(attribute_value, str):
            res = attribute_value[:128]
            value = res
        else:
            logger.warning("Could not serialize tag %s", attribute_key)
            continue
        tags[attribute_key] = value
    return tags


def _extract_annotations_from_events(events):
    if not events:
        return None
    annotations = []
    for event in events:
        annotations.append(
            {
                "timestamp": _nsec_to_usec_round(event.timestamp),
                "value": event.name,
            }
        )
    return annotations


def _nsec_to_usec_round(nsec):
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10 ** 3
