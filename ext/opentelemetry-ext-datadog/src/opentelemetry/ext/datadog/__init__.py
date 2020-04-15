import logging
import os
from urllib.parse import urlparse

from ddtrace.encoding import MsgpackEncoder
from ddtrace.internal.writer import AgentWriter
from ddtrace.span import Span as DatadogSpan

import opentelemetry.trace as trace_api
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.status import StatusCanonicalCode

log = logging.getLogger(__name__)

DEFAULT_AGENT_URL = "http://localhost:8126"
DATADOG_SPAN_TYPES = (
    "sql",
    "mongodb",
    "http",
)


class DatadogSpanExporter(SpanExporter):
    def __init__(self, agent_url=None, service=None):
        self.agent_url = (
            agent_url
            if agent_url
            else os.environ.get("DD_TRACE_AGENT_URL", DEFAULT_AGENT_URL)
        )
        self.service = service if service else os.environ.get("DD_SERVICE")
        self._agent_writer = None

    @property
    def agent_writer(self):
        if self._agent_writer is None:
            url_parsed = urlparse(self.agent_url)
            if url_parsed.scheme in ("http", "https"):
                self._agent_writer = AgentWriter(
                    hostname=url_parsed.hostname,
                    port=url_parsed.port,
                    https=url_parsed.scheme == "https",
                )
            elif url_parsed.scheme == "unix":
                self._agent_writer = AgentWriter(uds_path=url_parsed.path)
            else:
                raise ValueError(
                    "Unknown scheme `%s` for agent URL" % url_parsed.scheme
                )
        return self._agent_writer

    def export(self, spans):
        datadog_spans = self._translate_to_datadog(spans)

        self.agent_writer.write(spans=datadog_spans)

        return SpanExportResult.SUCCESS

    def shutdown(self):
        if self.agent_writer.started:
            self.agent_writer.stop()
            self.agent_writer.join(self.agent_writer.exit_timeout)

    def _translate_to_datadog(self, spans):
        datadog_spans = []

        for span in spans:
            trace_id, parent_id, span_id = _get_trace_ids(span)

            # datadog Span is initialized with a reference to the tracer which is
            # used to record the span when it is finished. We can skip ignore this
            # because we are not calling the finish method and explictly set the
            # duration.
            tracer = None

            datadog_span = DatadogSpan(
                tracer,
                span.name,
                service=self.service,
                resource=_get_resource(span),
                span_type=_get_span_type(span),
                trace_id=trace_id,
                span_id=span_id,
                parent_id=parent_id,
            )
            datadog_span.start_ns = span.start_time
            datadog_span.duration_ns = span.end_time - span.start_time
            datadog_span.error = (
                1
                if span.status.canonical_code is not StatusCanonicalCode.OK
                else 0
            )
            datadog_span.set_tags(span.attributes)

            # TODO: Add exception info

            datadog_spans.append(datadog_span)

        return datadog_spans


def _get_trace_ids(span):
    ctx = span.get_context()
    trace_id = ctx.trace_id
    span_id = ctx.span_id

    if isinstance(span.parent, trace_api.Span):
        parent_id = span.parent.get_context().span_id
    elif isinstance(span.parent, trace_api.SpanContext):
        parent_id = span.parent.span_id
    else:
        parent_id = 0

    trace_id = _convert_trace_id_uint64(trace_id)

    return trace_id, parent_id, span_id


def _convert_trace_id_uint64(otel_id):
    raw = otel_id.to_bytes(16, "big")
    return int.from_bytes(raw[8:], byteorder="big")


def _get_resource(span):
    if "http.method" in span.attributes:
        route = span.attributes.get(
            "http.route", span.attributes.get("http.path")
        )
        return (
            span.attributes["http.method"] + " " + route
            if route
            else span.attributes["http.method"]
        )

    return span.attributes.get("component", span.name)


def _get_span_type(span):
    # use db.type for database integrations (sql, mongodb) otherwise component
    span_type = span.attributes.get(
        "db.type", span.attributes.get("component")
    )
    span_type = span_type if span_type in DATADOG_SPAN_TYPES else None

    return span_type
