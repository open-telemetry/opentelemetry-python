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

import logging
import os
from urllib.parse import urlparse

from ddtrace.ext import SpanTypes as DatadogSpanTypes
from ddtrace.internal.writer import AgentWriter
from ddtrace.span import Span as DatadogSpan

import opentelemetry.trace as trace_api
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.status import StatusCanonicalCode

# pylint:disable=relative-beyond-top-level
from .constants import DD_ORIGIN, SAMPLE_RATE_METRIC_KEY

logger = logging.getLogger(__name__)


DEFAULT_AGENT_URL = "http://localhost:8126"
_INSTRUMENTATION_SPAN_TYPES = {
    "opentelemetry.ext.aiohttp-client": DatadogSpanTypes.HTTP,
    "opentelemetry.ext.asgi": DatadogSpanTypes.WEB,
    "opentelemetry.ext.dbapi": DatadogSpanTypes.SQL,
    "opentelemetry.ext.django": DatadogSpanTypes.WEB,
    "opentelemetry.ext.flask": DatadogSpanTypes.WEB,
    "opentelemetry.ext.grpc": DatadogSpanTypes.GRPC,
    "opentelemetry.ext.jinja2": DatadogSpanTypes.TEMPLATE,
    "opentelemetry.ext.mysql": DatadogSpanTypes.SQL,
    "opentelemetry.ext.psycopg2": DatadogSpanTypes.SQL,
    "opentelemetry.ext.pymemcache": DatadogSpanTypes.CACHE,
    "opentelemetry.ext.pymongo": DatadogSpanTypes.MONGODB,
    "opentelemetry.ext.pymysql": DatadogSpanTypes.SQL,
    "opentelemetry.ext.redis": DatadogSpanTypes.REDIS,
    "opentelemetry.ext.requests": DatadogSpanTypes.HTTP,
    "opentelemetry.ext.sqlalchemy": DatadogSpanTypes.SQL,
    "opentelemetry.ext.wsgi": DatadogSpanTypes.WEB,
}


class DatadogSpanExporter(SpanExporter):
    """Datadog span exporter for OpenTelemetry.

    Args:
        agent_url: The url of the Datadog Agent or use ``DD_TRACE_AGENT_URL`` environment variable
        service: The service to be used for the application or use ``DD_SERVICE`` environment variable
    """

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
                _get_span_name(span),
                service=self.service,
                resource=_get_resource(span),
                span_type=_get_span_type(span),
                trace_id=trace_id,
                span_id=span_id,
                parent_id=parent_id,
            )
            datadog_span.start_ns = span.start_time
            datadog_span.duration_ns = span.end_time - span.start_time

            if span.status.canonical_code is not StatusCanonicalCode.OK:
                datadog_span.error = 1
                if span.status.description:
                    exc_type, exc_val = _get_exc_info(span)
                    # no mapping for error.stack since traceback not recorded
                    datadog_span.set_tag("error.msg", exc_val)
                    datadog_span.set_tag("error.type", exc_type)

            datadog_span.set_tags(span.attributes)

            # add origin to root span
            origin = _get_origin(span)
            if origin and parent_id == 0:
                datadog_span.set_tag(DD_ORIGIN, origin)

            sampling_rate = _get_sampling_rate(span)
            if sampling_rate is not None:
                datadog_span.set_metric(SAMPLE_RATE_METRIC_KEY, sampling_rate)

            # span events and span links are not supported

            datadog_spans.append(datadog_span)

        return datadog_spans


def _get_trace_ids(span):
    """Extract tracer ids from span"""
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
    """Convert 128-bit int used for trace_id to 64-bit unsigned int"""
    return otel_id & 0xFFFFFFFFFFFFFFFF


def _get_span_name(span):
    """Get span name by using instrumentation and kind while backing off to
    span.name
    """
    instrumentation_name = (
        span.instrumentation_info.name if span.instrumentation_info else None
    )
    span_kind_name = span.kind.name if span.kind else None
    name = (
        "{}.{}".format(instrumentation_name, span_kind_name)
        if instrumentation_name and span_kind_name
        else span.name
    )
    return name


def _get_resource(span):
    """Get resource name for span"""
    if "http.method" in span.attributes:
        route = span.attributes.get(
            "http.route", span.attributes.get("http.path")
        )
        return (
            span.attributes["http.method"] + " " + route
            if route
            else span.attributes["http.method"]
        )

    return span.name


def _get_span_type(span):
    """Get Datadog span type"""
    instrumentation_name = (
        span.instrumentation_info.name if span.instrumentation_info else None
    )
    span_type = _INSTRUMENTATION_SPAN_TYPES.get(instrumentation_name)
    return span_type


def _get_exc_info(span):
    """Parse span status description for exception type and value"""
    exc_type, exc_val = span.status.description.split(":", 1)
    return exc_type, exc_val.strip()


def _get_origin(span):
    ctx = span.get_context()
    origin = ctx.trace_state.get(DD_ORIGIN)
    return origin


def _get_sampling_rate(span):
    ctx = span.get_context()
    return (
        span.sampler.rate
        if ctx.trace_flags.sampled
        and isinstance(span.sampler, trace_api.sampling.ProbabilitySampler)
        else None
    )
