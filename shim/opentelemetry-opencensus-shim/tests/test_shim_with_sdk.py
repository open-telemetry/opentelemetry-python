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
import unittest
from datetime import datetime

from opencensus.trace import execution_context, time_event
from opencensus.trace.span_context import SpanContext
from opencensus.trace.status import Status as OcStatus
from opencensus.trace.tracer import Tracer as OcTracer

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.shim.opencensus import install_shim, uninstall_shim

_TIMESTAMP = datetime.fromisoformat("2023-01-01T00:00:00.000000")


class TestShimWithSdk(unittest.TestCase):
    def setUp(self):
        uninstall_shim()
        self.tracer_provider = TracerProvider(
            sampler=ALWAYS_ON, shutdown_on_exit=False
        )
        self.mem_exporter = InMemorySpanExporter()
        self.tracer_provider.add_span_processor(
            SimpleSpanProcessor(self.mem_exporter)
        )
        install_shim(self.tracer_provider)

    def tearDown(self):
        uninstall_shim()

    def test_start_span_interacts_with_context(self):
        oc_tracer = OcTracer()
        span = oc_tracer.start_span("foo")

        # Should have created a real OTel span in implicit context under the hood. OpenCensus
        # does not require another step to set the span in context.
        otel_span = trace.get_current_span()
        self.assertNotEqual(span.span_id, 0)
        self.assertEqual(span.span_id, otel_span.get_span_context().span_id)

        # This should end the span and remove it from context
        oc_tracer.end_span()
        self.assertIs(trace.get_current_span(), trace.INVALID_SPAN)

    def test_start_span_interacts_with_oc_context(self):
        oc_tracer = OcTracer()
        span = oc_tracer.start_span("foo")

        # Should have put the shim span in OC's implicit context under the hood. OpenCensus
        # does not require another step to set the span in context.
        self.assertIs(execution_context.get_current_span(), span)

        # This should end the span and remove it from context
        oc_tracer.end_span()
        self.assertIs(execution_context.get_current_span(), None)

    def test_context_manager_interacts_with_context(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            # Should have created a real OTel span in implicit context under the hood
            otel_span = trace.get_current_span()

            self.assertNotEqual(span.span_id, 0)
            self.assertEqual(
                span.span_id, otel_span.get_span_context().span_id
            )

        # The span should now be popped from context
        self.assertIs(trace.get_current_span(), trace.INVALID_SPAN)

    def test_context_manager_interacts_with_oc_context(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            # Should have placed the shim span in implicit context under the hood
            self.assertIs(execution_context.get_current_span(), span)

        # The span should now be popped from context
        self.assertIs(execution_context.get_current_span(), None)

    def test_exports_a_span(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("span1"):
            pass

        self.assertEqual(len(self.mem_exporter.get_finished_spans()), 1)

    def test_uses_tracers_span_context_when_no_parent_in_context(self):
        # the SpanContext passed to the Tracer will become the parent when there is no span
        # already set in the OTel context
        oc_tracer = OcTracer(
            span_context=SpanContext(
                trace_id="ace0216bab2b7ba249761dbb19c871b7",
                span_id="1fead89ecf242225",
            )
        )

        with oc_tracer.start_span("span1"):
            pass

        exported_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        parent = exported_span.parent
        self.assertIsNotNone(parent)
        self.assertEqual(
            trace.format_trace_id(parent.trace_id),
            "ace0216bab2b7ba249761dbb19c871b7",
        )
        self.assertEqual(
            trace.format_span_id(parent.span_id), "1fead89ecf242225"
        )

    def test_ignores_tracers_span_context_when_parent_already_in_context(self):
        # the SpanContext passed to the Tracer will be ignored since there is already a span
        # set in the OTel context
        oc_tracer = OcTracer(
            span_context=SpanContext(
                trace_id="ace0216bab2b7ba249761dbb19c871b7",
                span_id="1fead89ecf242225",
            )
        )
        otel_tracer = self.tracer_provider.get_tracer(__name__)

        with otel_tracer.start_as_current_span("some_parent"):
            with oc_tracer.start_span("span1"):
                pass

        oc_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        otel_parent: ReadableSpan = self.mem_exporter.get_finished_spans()[1]
        self.assertEqual(
            oc_span.parent,
            otel_parent.context,
        )

    def test_span_attributes(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("span1") as span:
            span.add_attribute("key1", "value1")
            span.add_attribute("key2", "value2")

        exported_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        self.assertDictEqual(
            dict(exported_span.attributes),
            {"key1": "value1", "key2": "value2"},
        )

    def test_span_annotations(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("span1") as span:
            span.add_annotation("description", key1="value1", key2="value2")

        exported_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        self.assertEqual(len(exported_span.events), 1)
        event = exported_span.events[0]
        self.assertEqual(event.name, "description")
        self.assertDictEqual(
            dict(event.attributes), {"key1": "value1", "key2": "value2"}
        )

    def test_span_message_event(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("span1") as span:
            span.add_message_event(
                time_event.MessageEvent(
                    _TIMESTAMP, "id_sent", time_event.Type.SENT, "20", "10"
                )
            )
            span.add_message_event(
                time_event.MessageEvent(
                    _TIMESTAMP,
                    "id_received",
                    time_event.Type.RECEIVED,
                    "20",
                    "10",
                )
            )
            span.add_message_event(
                time_event.MessageEvent(
                    _TIMESTAMP,
                    "id_unspecified",
                    None,
                    "20",
                    "10",
                )
            )

        exported_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        self.assertEqual(len(exported_span.events), 3)
        event1, event2, event3 = exported_span.events

        self.assertEqual(event1.name, "id_sent")
        self.assertDictEqual(
            dict(event1.attributes),
            {
                "message.event.size.compressed": "10",
                "message.event.size.uncompressed": "20",
                "message.event.type": "SENT",
            },
        )
        self.assertEqual(event2.name, "id_received")
        self.assertDictEqual(
            dict(event2.attributes),
            {
                "message.event.size.compressed": "10",
                "message.event.size.uncompressed": "20",
                "message.event.type": "RECEIVED",
            },
        )
        self.assertEqual(event3.name, "id_unspecified")
        self.assertDictEqual(
            dict(event3.attributes),
            {
                "message.event.size.compressed": "10",
                "message.event.size.uncompressed": "20",
                "message.event.type": "TYPE_UNSPECIFIED",
            },
        )

    def test_span_status(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("span_ok") as span:
            # OTel will log about the message being set on a not OK span
            with self.assertLogs(level=logging.WARNING) as rec:
                span.set_status(OcStatus(0, "message"))
            self.assertIn(
                "description should only be set when status_code is set to StatusCode.ERROR",
                rec.output[0],
            )

        with oc_tracer.start_span("span_exception") as span:
            span.set_status(
                OcStatus.from_exception(Exception("exception message"))
            )

        self.assertEqual(len(self.mem_exporter.get_finished_spans()), 2)
        ok_span: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        exc_span: ReadableSpan = self.mem_exporter.get_finished_spans()[1]

        self.assertTrue(ok_span.status.is_ok)
        # should be none even though we provided it because OTel drops the description when
        # status is not ERROR
        self.assertIsNone(ok_span.status.description)

        self.assertFalse(exc_span.status.is_ok)
        self.assertEqual(exc_span.status.description, "exception message")

    def assert_related(self, *, child: ReadableSpan, parent: ReadableSpan):
        self.assertEqual(
            child.parent.span_id, parent.get_span_context().span_id
        )

    def test_otel_sandwich(self):
        oc_tracer = OcTracer()
        otel_tracer = self.tracer_provider.get_tracer(__name__)
        with oc_tracer.start_span("opencensus_outer"):
            with otel_tracer.start_as_current_span("otel_middle"):
                with oc_tracer.start_span("opencensus_inner"):
                    pass

        self.assertEqual(len(self.mem_exporter.get_finished_spans()), 3)
        opencensus_inner: ReadableSpan = (
            self.mem_exporter.get_finished_spans()[0]
        )
        otel_middle: ReadableSpan = self.mem_exporter.get_finished_spans()[1]
        opencensus_outer: ReadableSpan = (
            self.mem_exporter.get_finished_spans()[2]
        )

        self.assertEqual(opencensus_outer.name, "opencensus_outer")
        self.assertEqual(otel_middle.name, "otel_middle")
        self.assertEqual(opencensus_inner.name, "opencensus_inner")

        self.assertIsNone(opencensus_outer.parent)
        self.assert_related(parent=opencensus_outer, child=otel_middle)
        self.assert_related(parent=otel_middle, child=opencensus_inner)

    def test_opencensus_sandwich(self):
        oc_tracer = OcTracer()
        otel_tracer = self.tracer_provider.get_tracer(__name__)
        with otel_tracer.start_as_current_span("otel_outer"):
            with oc_tracer.start_span("opencensus_middle"):
                with otel_tracer.start_as_current_span("otel_inner"):
                    pass

        self.assertEqual(len(self.mem_exporter.get_finished_spans()), 3)
        otel_inner: ReadableSpan = self.mem_exporter.get_finished_spans()[0]
        opencensus_middle: ReadableSpan = (
            self.mem_exporter.get_finished_spans()[1]
        )
        otel_outer: ReadableSpan = self.mem_exporter.get_finished_spans()[2]

        self.assertEqual(otel_outer.name, "otel_outer")
        self.assertEqual(opencensus_middle.name, "opencensus_middle")
        self.assertEqual(otel_inner.name, "otel_inner")

        self.assertIsNone(otel_outer.parent)
        self.assert_related(parent=otel_outer, child=opencensus_middle)
        self.assert_related(parent=opencensus_middle, child=otel_inner)
