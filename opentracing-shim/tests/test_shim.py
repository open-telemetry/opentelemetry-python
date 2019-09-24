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

import unittest

import opentracing

import opentracingshim
from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer


class TestShim(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.tracer()
        self.shim = opentracingshim.create_tracer(self.tracer)

    @classmethod
    def setUpClass(cls):
        """Set preferred tracer implementation only once rather than before
        every test method.
        """
        # TODO: Do we need to call setUpClass() on super()?
        # Seems to work fine without it.
        super(TestShim, cls).setUpClass()
        trace.set_preferred_tracer_implementation(lambda T: Tracer())

    def test_shim_type(self):
        # Verify shim is an OpenTracing tracer.
        self.assertIsInstance(self.shim, opentracing.Tracer)

    def test_start_active_span(self):
        with self.shim.start_active_span("TestSpan") as scope:
            self.assertIsInstance(scope, opentracing.Scope)
            self.assertIsInstance(scope.span, opentracing.Span)

            # Verify the span is active in the OpenTelemetry tracer.
            # TODO: We can't check for equality of self.shim.active_span and
            # scope.span because the same OpenTelemetry span is returned inside
            # different SpanWrapper objects. Is this a problem?
            self.assertEqual(self.shim.active_span.context, scope.span.context)

        # Verify the span has ended in the OpenTelemetry tracer.
        self.assertIsNotNone(scope.span.otel_span.end_time)
        self.assertIsNone(self.tracer.get_current_span())

    def test_parent_child(self):
        with self.shim.start_active_span("ParentSpan") as parent:
            parent_trace_id = parent.span.otel_span.get_context().trace_id

            # Verify parent span is the active span.
            self.assertEqual(
                self.shim.active_span.context, parent.span.context
            )

            with self.shim.start_active_span("ChildSpan") as child:
                child_trace_id = child.span.otel_span.get_context().trace_id

                # Verify child span is the active span.
                self.assertEqual(
                    self.shim.active_span.context, child.span.context
                )

                # Verify parent-child relationship.
                self.assertEqual(parent_trace_id, child_trace_id)
                self.assertEqual(
                    child.span.otel_span.parent, parent.span.otel_span
                )

            # Verify parent span becomes the active span again.
            self.assertEqual(
                self.shim.active_span.context, parent.span.context
            )

        # Verify there is no active span.
        self.assertIsNone(self.shim.active_span)

    def test_start_span(self):
        span = self.shim.start_span("TestSpan")

        self.assertIsInstance(span, opentracing.Span)

        # Verify the span is started.
        self.assertIsNotNone(span.otel_span.start_time)

    def test_explicit_parent(self):
        # Test explicit parent of type Span.
        parent = self.shim.start_span("ParentSpan")
        child = self.shim.start_span("ChildSpan", child_of=parent)

        parent_trace_id = parent.otel_span.get_context().trace_id
        child_trace_id = child.otel_span.get_context().trace_id

        self.assertEqual(child_trace_id, parent_trace_id)
        self.assertEqual(child.otel_span.parent, parent.otel_span)

        # Test explicit parent of type SpanContext.
        parent = self.shim.start_span("ParentSpan")
        child = self.shim.start_span(
            "SpanWithContextParent", child_of=parent.context
        )

        parent_trace_id = parent.otel_span.get_context().trace_id
        child_trace_id = child.otel_span.get_context().trace_id

        self.assertEqual(child_trace_id, parent_trace_id)
        self.assertEqual(child.otel_span.parent, parent.context)

    def test_set_operation_name(self):
        with self.shim.start_active_span("TestName") as scope:
            self.assertEqual(scope.span.otel_span.name, "TestName")

            scope.span.set_operation_name("NewName")
            self.assertEqual(scope.span.otel_span.name, "NewName")

    def test_set_tag(self):
        with self.shim.start_active_span("TestSetTag") as scope:
            with self.assertRaises(KeyError):
                # pylint: disable=pointless-statement
                scope.span.otel_span.attributes["my"]

            scope.span.set_tag("my", "tag")
            self.assertEqual(scope.span.otel_span.attributes["my"], "tag")

    def test_span(self):
        pass
        # TODO: Verify finish() on span.

    def test_span_context(self):
        otel_context = trace.SpanContext(1234, 5678)
        context = opentracingshim.SpanContextWrapper(otel_context)

        self.assertIsInstance(context, opentracing.SpanContext)
        self.assertEqual(context.otel_context.trace_id, 1234)
        self.assertEqual(context.otel_context.span_id, 5678)
