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
from unittest.mock import patch

from opencensus.trace import trace_options, tracestate
from opencensus.trace.blank_span import BlankSpan as OcBlankSpan
from opencensus.trace.link import Link as OcLink
from opencensus.trace.span import SpanKind
from opencensus.trace.span_context import SpanContext
from opencensus.trace.tracer import Tracer as OcTracer
from opencensus.trace.tracers.noop_tracer import NoopTracer as OcNoopTracer

from opentelemetry import context, trace
from opentelemetry.shim.opencensus import install_shim, uninstall_shim
from opentelemetry.shim.opencensus._shim_span import ShimSpan
from opentelemetry.shim.opencensus._shim_tracer import (
    ShimTracer,
    set_oc_span_in_context,
)


class TestShim(unittest.TestCase):
    def setUp(self):
        uninstall_shim()
        install_shim()

    def tearDown(self):
        uninstall_shim()

    def assert_hasattr(self, obj, key):
        self.assertTrue(hasattr(obj, key))

    def test_shim_tracer_wraps_noop_tracer(self):
        oc_tracer = OcTracer()

        self.assertIsInstance(oc_tracer.tracer, ShimTracer)

        # wrapt.ObjectProxy does the magic here. The ShimTracer should look like the real OC
        # NoopTracer.
        self.assertIsInstance(oc_tracer.tracer, OcNoopTracer)
        self.assert_hasattr(oc_tracer.tracer, "finish")
        self.assert_hasattr(oc_tracer.tracer, "span")
        self.assert_hasattr(oc_tracer.tracer, "start_span")
        self.assert_hasattr(oc_tracer.tracer, "end_span")
        self.assert_hasattr(oc_tracer.tracer, "current_span")
        self.assert_hasattr(oc_tracer.tracer, "add_attribute_to_current_span")
        self.assert_hasattr(oc_tracer.tracer, "list_collected_spans")

    def test_shim_tracer_starts_shim_spans(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            self.assertIsInstance(span, ShimSpan)

    def test_shim_span_wraps_blank_span(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            # wrapt.ObjectProxy does the magic here. The ShimSpan should look like the real OC
            # BlankSpan.
            self.assertIsInstance(span, OcBlankSpan)

            # members
            self.assert_hasattr(span, "name")
            self.assert_hasattr(span, "parent_span")
            self.assert_hasattr(span, "start_time")
            self.assert_hasattr(span, "end_time")
            self.assert_hasattr(span, "span_id")
            self.assert_hasattr(span, "attributes")
            self.assert_hasattr(span, "stack_trace")
            self.assert_hasattr(span, "annotations")
            self.assert_hasattr(span, "message_events")
            self.assert_hasattr(span, "links")
            self.assert_hasattr(span, "status")
            self.assert_hasattr(span, "same_process_as_parent_span")
            self.assert_hasattr(span, "_child_spans")
            self.assert_hasattr(span, "context_tracer")
            self.assert_hasattr(span, "span_kind")

            # methods
            self.assert_hasattr(span, "on_create")
            self.assert_hasattr(span, "children")
            self.assert_hasattr(span, "span")
            self.assert_hasattr(span, "add_attribute")
            self.assert_hasattr(span, "add_annotation")
            self.assert_hasattr(span, "add_message_event")
            self.assert_hasattr(span, "add_link")
            self.assert_hasattr(span, "set_status")
            self.assert_hasattr(span, "start")
            self.assert_hasattr(span, "finish")
            self.assert_hasattr(span, "__iter__")
            self.assert_hasattr(span, "__enter__")
            self.assert_hasattr(span, "__exit__")

    def test_add_link_logs_a_warning(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            with self.assertLogs(level=logging.WARNING):
                span.add_link(OcLink("1", "1"))

    def test_set_span_kind_logs_a_warning(self):
        oc_tracer = OcTracer()
        with oc_tracer.start_span("foo") as span:
            with self.assertLogs(level=logging.WARNING):
                span.span_kind = SpanKind.CLIENT

    # pylint: disable=no-self-use,no-member,protected-access
    def test_shim_span_contextmanager_calls_does_not_call_end(self):
        # This was a bug in first implementation where the underlying OTel span.end() was
        # called after span.__exit__ which caused double-ending the span.
        oc_tracer = OcTracer()
        oc_span = oc_tracer.start_span("foo")

        with patch.object(
            oc_span,
            "_self_otel_span",
            wraps=oc_span._self_otel_span,
        ) as spy_otel_span:
            with oc_span:
                pass

        spy_otel_span.end.assert_not_called()

    def test_set_oc_span_in_context_no_span_id(self):
        # This won't create a span ID and is the default behavior if you don't pass a context
        # when creating the Tracer
        ctx = set_oc_span_in_context(SpanContext(), context.get_current())
        self.assertIs(trace.get_current_span(ctx), trace.INVALID_SPAN)

    def test_set_oc_span_in_context_ids(self):
        ctx = set_oc_span_in_context(
            SpanContext(
                trace_id="ace0216bab2b7ba249761dbb19c871b7",
                span_id="1fead89ecf242225",
            ),
            context.get_current(),
        )
        span_ctx = trace.get_current_span(ctx).get_span_context()

        self.assertEqual(
            trace.format_trace_id(span_ctx.trace_id),
            "ace0216bab2b7ba249761dbb19c871b7",
        )
        self.assertEqual(
            trace.format_span_id(span_ctx.span_id), "1fead89ecf242225"
        )

    def test_set_oc_span_in_context_remote(self):
        for is_from_remote in True, False:
            ctx = set_oc_span_in_context(
                SpanContext(
                    trace_id="ace0216bab2b7ba249761dbb19c871b7",
                    span_id="1fead89ecf242225",
                    from_header=is_from_remote,
                ),
                context.get_current(),
            )
            span_ctx = trace.get_current_span(ctx).get_span_context()
            self.assertEqual(span_ctx.is_remote, is_from_remote)

    def test_set_oc_span_in_context_traceoptions(self):
        for oc_trace_options, expect in [
            # Not sampled
            (
                trace_options.TraceOptions("0"),
                trace.TraceFlags(trace.TraceFlags.DEFAULT),
            ),
            # Sampled
            (
                trace_options.TraceOptions("1"),
                trace.TraceFlags(trace.TraceFlags.SAMPLED),
            ),
        ]:
            ctx = set_oc_span_in_context(
                SpanContext(
                    trace_id="ace0216bab2b7ba249761dbb19c871b7",
                    span_id="1fead89ecf242225",
                    trace_options=oc_trace_options,
                ),
                context.get_current(),
            )
            span_ctx = trace.get_current_span(ctx).get_span_context()
            self.assertEqual(span_ctx.trace_flags, expect)

    def test_set_oc_span_in_context_tracestate(self):
        ctx = set_oc_span_in_context(
            SpanContext(
                trace_id="ace0216bab2b7ba249761dbb19c871b7",
                span_id="1fead89ecf242225",
                tracestate=tracestate.Tracestate({"hello": "tracestate"}),
            ),
            context.get_current(),
        )
        span_ctx = trace.get_current_span(ctx).get_span_context()
        self.assertEqual(
            span_ctx.trace_state, trace.TraceState([("hello", "tracestate")])
        )
