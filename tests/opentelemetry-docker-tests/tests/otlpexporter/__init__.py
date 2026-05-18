# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from abc import ABC, abstractmethod

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.test.otlp_test_server import OtlpProtoTestServer


def _attrs_to_dict(attributes) -> dict:
    result = {}
    for kv in attributes:
        which = kv.value.WhichOneof("value")
        if which == "string_value":
            result[kv.key] = kv.value.string_value
        elif which == "int_value":
            result[kv.key] = kv.value.int_value
        elif which == "double_value":
            result[kv.key] = kv.value.double_value
        elif which == "bool_value":
            result[kv.key] = kv.value.bool_value
    return result


class TracesExporterTestsBase(ABC, unittest.TestCase):
    __test__ = False

    _server: OtlpProtoTestServer

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._server = OtlpProtoTestServer(host="0.0.0.0", port=4319).start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._tracer_provider = TracerProvider()
        self._tracer_provider.add_span_processor(
            SimpleSpanProcessor(self.build_exporter())
        )
        self._tracer = self._tracer_provider.get_tracer(__name__)
        self._server.clear()

    def tearDown(self):
        self._tracer_provider.shutdown()
        super().tearDown()

    @abstractmethod
    def build_exporter(self) -> SpanExporter: ...

    def test_simple_span_name(self):
        with self._tracer.start_as_current_span("my-span"):
            pass

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.name, "my-span")

    def test_span_attributes(self):
        with self._tracer.start_as_current_span(
            "attrs-span",
            attributes={
                "str_key": "hello",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
            },
        ):
            pass

        recorded = self._server.get_span(timeout=5.0)
        attrs = _attrs_to_dict(recorded.span.attributes)
        self.assertEqual(attrs["str_key"], "hello")
        self.assertEqual(attrs["int_key"], 42)
        self.assertAlmostEqual(attrs["float_key"], 3.14, places=5)
        self.assertEqual(attrs["bool_key"], True)

    def test_nested_spans_parent_child(self):
        with self._tracer.start_as_current_span("foo"):
            with self._tracer.start_as_current_span("bar"):
                with self._tracer.start_as_current_span("baz"):
                    pass

        spans = {
            r.span.name: r.span
            for r in self._server.get_spans(count=3, timeout=10.0)
        }
        self.assertIn("foo", spans)
        self.assertIn("bar", spans)
        self.assertIn("baz", spans)
        self.assertEqual(spans["baz"].parent_span_id, spans["bar"].span_id)
        self.assertEqual(spans["bar"].parent_span_id, spans["foo"].span_id)
        self.assertEqual(spans["foo"].parent_span_id, b"")

    def test_span_with_event(self):
        with self._tracer.start_as_current_span("event-span") as span:
            span.add_event("my-event", {"event_key": "event_val"})

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(len(recorded.span.events), 1)
        event = recorded.span.events[0]
        self.assertEqual(event.name, "my-event")
        self.assertEqual(
            _attrs_to_dict(event.attributes), {"event_key": "event_val"}
        )

    def test_span_with_link(self):
        from opentelemetry.trace import Link, SpanContext, TraceFlags

        link_trace_id = 0x000000000000000000000000DEADBEEF
        link_span_id = 0x00000000DEADBEF0
        link_context = SpanContext(
            trace_id=link_trace_id,
            span_id=link_span_id,
            is_remote=True,
            trace_flags=TraceFlags(0x01),
        )
        with self._tracer.start_as_current_span(
            "linked-span", links=[Link(link_context)]
        ):
            pass

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(len(recorded.span.links), 1)
        link = recorded.span.links[0]
        self.assertEqual(link.trace_id, link_trace_id.to_bytes(16, "big"))
        self.assertEqual(link.span_id, link_span_id.to_bytes(8, "big"))

    def test_span_status_ok(self):
        from opentelemetry.trace import StatusCode

        with self._tracer.start_as_current_span("ok-span") as span:
            span.set_status(StatusCode.OK)

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.status.code, 1)  # proto OK = 1

    def test_span_status_error(self):
        from opentelemetry.trace import StatusCode

        with self._tracer.start_as_current_span("error-span") as span:
            span.set_status(StatusCode.ERROR, "something went wrong")

        recorded = self._server.get_span(timeout=5.0)
        self.assertEqual(recorded.span.status.code, 2)  # proto ERROR = 2
        self.assertEqual(recorded.span.status.message, "something went wrong")
