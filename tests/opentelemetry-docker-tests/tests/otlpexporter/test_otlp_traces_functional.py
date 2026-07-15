# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
from collections.abc import Iterator

import pytest
from grpc import Compression as GRPCCompression
from inline_snapshot import snapshot

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http import (
    Compression as HTTPCompression,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.test._otlp_test_server import OtlpProtoTestServer
from opentelemetry.trace import Link, SpanContext, StatusCode, TraceFlags

from . import CUSTOM_HEADERS, ExporterConfig, _attrs_to_dict

TRACE_EXPORTER_CONFIGS: list[ExporterConfig[SpanExporter]] = [
    ExporterConfig(
        id="http-urllib3",
        exporter_class=HTTPSpanExporter,
        kwargs={"endpoint": "http://localhost:4318/v1/traces"},
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests",
        exporter_class=HTTPSpanExporter,
        kwargs={"endpoint": "http://localhost:4318/v1/traces"},
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-deflate",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "compression": HTTPCompression.Deflate,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-deflate",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "compression": HTTPCompression.Deflate,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-gzip",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "compression": HTTPCompression.Gzip,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-gzip",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "compression": HTTPCompression.Gzip,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-headers",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "headers": CUSTOM_HEADERS,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-headers",
        exporter_class=HTTPSpanExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/traces",
            "headers": CUSTOM_HEADERS,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="grpc",
        exporter_class=GRPCSpanExporter,
        kwargs={"insecure": True},
    ),
    ExporterConfig(
        id="grpc-gzip",
        exporter_class=GRPCSpanExporter,
        kwargs={"insecure": True, "compression": GRPCCompression.Gzip},
    ),
    ExporterConfig(
        id="grpc-headers",
        exporter_class=GRPCSpanExporter,
        kwargs={"insecure": True, "headers": CUSTOM_HEADERS},
    ),
]


class TestTracesExporter:
    @pytest.fixture(
        scope="class", params=TRACE_EXPORTER_CONFIGS, ids=lambda c: c.id
    )
    def config(self, request) -> ExporterConfig[SpanExporter]:
        return request.param

    @pytest.fixture(scope="class")
    def tracer(
        self,
        config: ExporterConfig[SpanExporter],
        server: OtlpProtoTestServer,
    ) -> Iterator[Tracer]:
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(config.build()))
        try:
            yield tracer_provider.get_tracer(__name__)
        finally:
            tracer_provider.shutdown()

    @pytest.fixture(autouse=True)
    def clear_server(self, server: OtlpProtoTestServer) -> None:
        server.clear()

    def test_simple_span_name(
        self, tracer: Tracer, server: OtlpProtoTestServer
    ):
        with tracer.start_as_current_span("my-span"):
            pass

        recorded = server.get_span(timeout=5.0)
        assert recorded.span.name == "my-span"

    def test_span_attributes(
        self, tracer: Tracer, server: OtlpProtoTestServer
    ):
        with tracer.start_as_current_span(
            "attrs-span",
            attributes={
                "str_key": "hello",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
            },
        ):
            pass

        recorded = server.get_span(timeout=5.0)
        attrs = _attrs_to_dict(recorded.span.attributes)
        assert math.isclose(attrs.pop("float_key"), 3.14, abs_tol=1e-5)
        assert attrs == snapshot(
            {"str_key": "hello", "int_key": 42, "bool_key": True}
        )

    def test_nested_spans_parent_child(
        self, tracer: Tracer, server: OtlpProtoTestServer
    ):
        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    pass

        spans = {
            r.span.name: r.span
            for r in server.get_spans(count=3, timeout=10.0)
        }
        assert set(spans.keys()) == snapshot({"bar", "baz", "foo"})
        assert spans["baz"].parent_span_id == spans["bar"].span_id
        assert spans["bar"].parent_span_id == spans["foo"].span_id
        assert spans["foo"].parent_span_id == b""

    def test_span_with_event(
        self, tracer: Tracer, server: OtlpProtoTestServer
    ):
        with tracer.start_as_current_span("event-span") as span:
            span.add_event("my-event", {"event_key": "event_val"})

        recorded = server.get_span(timeout=5.0)
        assert len(recorded.span.events) == 1
        event = recorded.span.events[0]
        assert event.name == "my-event"
        assert _attrs_to_dict(event.attributes) == snapshot(
            {"event_key": "event_val"}
        )

    def test_span_with_link(self, tracer: Tracer, server: OtlpProtoTestServer):
        link_trace_id = 0x000000000000000000000000DEADBEEF
        link_span_id = 0x00000000DEADBEF0
        link_context = SpanContext(
            trace_id=link_trace_id,
            span_id=link_span_id,
            is_remote=True,
            trace_flags=TraceFlags(0x01),
        )
        with tracer.start_as_current_span(
            "linked-span", links=[Link(link_context)]
        ):
            pass

        recorded = server.get_span(timeout=5.0)
        assert len(recorded.span.links) == 1
        link = recorded.span.links[0]
        assert link.trace_id == link_trace_id.to_bytes(16, "big")
        assert link.span_id == link_span_id.to_bytes(8, "big")

    def test_span_status_ok(self, tracer: Tracer, server: OtlpProtoTestServer):
        with tracer.start_as_current_span("ok-span") as span:
            span.set_status(StatusCode.OK)

        recorded = server.get_span(timeout=5.0)
        assert recorded.span.status.code == snapshot(1)

    def test_span_status_error(
        self, tracer: Tracer, server: OtlpProtoTestServer
    ):
        with tracer.start_as_current_span("error-span") as span:
            span.set_status(StatusCode.ERROR, "something went wrong")

        recorded = server.get_span(timeout=5.0)
        assert recorded.span.status.code == snapshot(2)
        assert recorded.span.status.message == snapshot("something went wrong")
