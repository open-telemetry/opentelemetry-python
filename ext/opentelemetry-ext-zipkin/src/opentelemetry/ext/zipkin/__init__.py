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

Installation
------------

::

     pip install opentelemetry-ext-zipkin


Usage
-----

The **OpenTelemetry Zipkin Exporter** allows to export `OpenTelemetry`_ traces to `Zipkin`_.
This exporter always send traces to the configured Zipkin collector using HTTP.


.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext import zipkin
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a ZipkinSpanExporter
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        service_name="my-helloworld-service",
        # optional:
        # host_name="localhost",
        # port=9411,
        # endpoint="/api/v2/spans",
        # protocol="http",
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

API
---
"""

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
DEFAULT_RETRY = False
ZIPKIN_HEADERS = {"Content-Type": "application/json"}

SPAN_KIND_MAP = {
    SpanKind.INTERNAL: None,
    SpanKind.SERVER: "SERVER",
    SpanKind.CLIENT: "CLIENT",
    SpanKind.PRODUCER: "PRODUCER",
    SpanKind.CONSUMER: "CONSUMER",
}

SUCCESS_STATUS_CODES = (200, 202)

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
        retry: Set to True to configure the exporter to retry on failure.
    """

    def __init__(
        self,
        service_name: str,
        host_name: str = DEFAULT_HOST_NAME,
        port: int = DEFAULT_PORT,
        endpoint: str = DEFAULT_ENDPOINT,
        protocol: str = DEFAULT_PROTOCOL,
        ipv4: Optional[str] = None,
        ipv6: Optional[str] = None,
        retry: Optional[str] = DEFAULT_RETRY,
    ):
        self.service_name = service_name
        self.host_name = host_name
        self.port = port
        self.endpoint = endpoint
        self.protocol = protocol
        self.url = "{}://{}:{}{}".format(
            self.protocol, self.host_name, self.port, self.endpoint
        )
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.retry = retry

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        zipkin_spans = self._translate_to_zipkin(spans)
        result = requests.post(
            url=self.url, data=json.dumps(zipkin_spans), headers=ZIPKIN_HEADERS
        )

        if result.status_code not in SUCCESS_STATUS_CODES:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )

            if self.retry:
                return SpanExportResult.FAILED_RETRYABLE
            return SpanExportResult.FAILED_NOT_RETRYABLE
        return SpanExportResult.SUCCESS

    def _translate_to_zipkin(self, spans: Sequence[Span]):

        local_endpoint = {"serviceName": self.service_name, "port": self.port}

        if self.ipv4 is not None:
            local_endpoint["ipv4"] = self.ipv4

        if self.ipv6 is not None:
            local_endpoint["ipv6"] = self.ipv6

        zipkin_spans = []
        for span in spans:
            context = span.get_context()
            trace_id = context.trace_id
            span_id = context.span_id

            # Timestamp in zipkin spans is int of microseconds.
            # see: https://zipkin.io/pages/instrumenting.html
            start_timestamp_mus = _nsec_to_usec_round(span.start_time)
            duration_mus = _nsec_to_usec_round(span.end_time - span.start_time)

            zipkin_span = {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span.name,
                "timestamp": start_timestamp_mus,
                "duration": duration_mus,
                "localEndpoint": local_endpoint,
                "kind": SPAN_KIND_MAP[span.kind],
                "tags": _extract_tags_from_span(span.attributes),
                "annotations": _extract_annotations_from_events(span.events),
            }

            if context.trace_flags.sampled:
                zipkin_span["debug"] = 1

            if isinstance(span.parent, Span):
                zipkin_span["parentId"] = format(
                    span.parent.get_context().span_id, "x"
                )
            elif isinstance(span.parent, SpanContext):
                zipkin_span["parentId"] = format(span.parent.span_id, "x")

            zipkin_spans.append(zipkin_span)
        return zipkin_spans

    def shutdown(self) -> None:
        pass


def _extract_tags_from_span(attr):
    if not attr:
        return None
    tags = {}
    for attribute_key, attribute_value in attr.items():
        if isinstance(attribute_value, (int, bool, float)):
            value = str(attribute_value)
        elif isinstance(attribute_value, str):
            value = attribute_value[:128]
        else:
            logger.warning("Could not serialize tag %s", attribute_key)
            continue
        tags[attribute_key] = value
    return tags


def _extract_annotations_from_events(events):
    return (
        [
            {"timestamp": _nsec_to_usec_round(e.timestamp), "value": e.name}
            for e in events
        ]
        if events
        else None
    )


def _nsec_to_usec_round(nsec):
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10 ** 3
