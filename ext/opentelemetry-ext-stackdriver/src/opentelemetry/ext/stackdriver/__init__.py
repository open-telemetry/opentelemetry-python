# Copyright 2018, OpenCensus Authors
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

"""Stackdriver Span Exporter for OpenTelemetry."""

import base64
import datetime
import logging
import socket

from google.cloud.trace import trace_service_client
from google.cloud.trace.client import Client
from google.cloud.trace_v2.proto import trace_pb2

import opentelemetry.trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk.trace.export import Span, SpanExporter, SpanExportResult
from opentelemetry.sdk.util import ns_to_iso_str

from .utils import (
    extract_attributes,
    extract_events,
    extract_links,
    extract_status,
    get_truncatable_str,
    map_attributes,
)
from .version import __version__

logger = logging.getLogger(__name__)

AGENT = "opentelemetry-python [{}]".format(__version__)


class StackdriverSpanExporter(SpanExporter):
    """Stackdriver span exporter for OpenTelemetry.

    Args:
        client: Stackdriver Trace client.
        project_id: project_id to create the Trace client.
    """

    def __init__(
        self, client=None, project_id=None,
    ):
        if client is None:
            client = Client(project=project_id)
            # initialize a authed client to prevent recorded in span
            client.batch_write_spans(
                "projects/{}".format(project_id), {"spans": []}
            )
        self.client = client
        self.project_id = self.client.project

    def export(self, spans: Span):
        """Export the spans to Stackdriver.

        Args:
            spans: Tuple of spans to export
        """
        stackdriver_spans = self.translate_to_stackdriver(spans)

        self.client.batch_write_spans(
            "projects/{}".format(self.project_id), {"spans": stackdriver_spans}
        )

        return SpanExportResult.SUCCESS

    def translate_to_stackdriver(self, spans: Span):
        """Translate the spans to Stackdriver format.

        Args:
            spans: Tuple of spans to convert
        """

        stackdriver_spans = []

        for span in spans:
            ctx = span.get_context()
            trace_id = "{:032x}".format(ctx.trace_id)
            span_id = "{:016x}".format(ctx.span_id)

            parent_id = None
            if isinstance(span.parent, trace_api.Span):
                parent_id = "{:016x}".format(span.parent.get_context().span_id)
            elif isinstance(span.parent, trace_api.SpanContext):
                parent_id = "{:016x}".format(span.parent.span_id)

            span_name = "projects/{}/traces/{}/spans/{}".format(
                self.project_id, trace_id, span_id
            )

            span.attributes["g.co/agent"] = AGENT
            attr_map = extract_attributes(span.attributes)
            formatted_time_events = extract_events(span.events)

            sd_span = {
                "name": span_name,
                "spanId": span_id,
                "parentSpanId": parent_id,
                "displayName": get_truncatable_str(span.name),
                "attributes": map_attributes(attr_map),
                "links": extract_links(span.links),
                "status": extract_status(span.status),
            }
            sd_span["parentSpanId"] = parent_id
            sd_span["timeEvents"] = (
                {"timeEvent": formatted_time_events}
                if formatted_time_events
                else None
            )
            sd_span["startTime"] = (
                ns_to_iso_str(span.start_time) if span.start_time else None
            )
            sd_span["endTime"] = (
                ns_to_iso_str(span.end_time) if span.end_time else None
            )

            stackdriver_spans.append(sd_span)

        return stackdriver_spans

    def shutdown(self):
        pass
