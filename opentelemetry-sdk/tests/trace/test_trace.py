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

from unittest import mock
import contextvars
import unittest

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace


class TestTracer(unittest.TestCase):

    def test_extends_api(self):
        tracer = trace.Tracer()
        self.assertIsInstance(tracer, trace_api.Tracer)


class TestSpanCreation(unittest.TestCase):

    def test_start_span_implicit(self):
        context = contextvars.ContextVar('test_start_span_implicit')
        tracer = trace.Tracer(context)

        self.assertIsNone(tracer.get_current_span())

        with tracer.start_span('root') as root:
            self.assertIs(tracer.get_current_span(), root)

            self.assertIsNotNone(root.start_time)
            self.assertIsNone(root.end_time)

            with tracer.start_span('child') as child:
                self.assertIs(tracer.get_current_span(), child)
                self.assertIs(child.parent, root)

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The new child span should inherit the parent's context but
                # get a new span ID.
                root_context = root.get_context()
                child_context = child.get_context()
                self.assertEqual(root_context.trace_id, child_context.trace_id)
                self.assertNotEqual(root_context.span_id,
                                    child_context.span_id)
                self.assertEqual(root_context.trace_state,
                                 child_context.trace_state)
                self.assertEqual(root_context.trace_options,
                                 child_context.trace_options)

            # After exiting the child's scope the parent should become the
            # current span again.
            self.assertIs(tracer.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

        self.assertIsNone(tracer.get_current_span())
        self.assertIsNotNone(root.end_time)

    def test_start_span_explicit(self):
        context = contextvars.ContextVar('test_start_span_explicit')
        tracer = trace.Tracer(context)

        other_parent = trace_api.SpanContext(
            trace_id=0x000000000000000000000000deadbeef,
            span_id=0x00000000deadbef0
        )

        self.assertIsNone(tracer.get_current_span())

        # Test with the implicit root span
        with tracer.start_span('root') as root:
            self.assertIs(tracer.get_current_span(), root)

            self.assertIsNotNone(root.start_time)
            self.assertIsNone(root.end_time)

            with tracer.start_span('stepchild', other_parent) as child:
                # The child should become the current span as usual, but its
                # parent should be the one passed in, not the
                # previously-current span.
                self.assertIs(tracer.get_current_span(), child)
                self.assertNotEqual(child.parent, root)
                self.assertIs(child.parent, other_parent)

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The child should inherit its context fromr the explicit
                # parent, not the previously-current span.
                child_context = child.get_context()
                self.assertEqual(other_parent.trace_id, child_context.trace_id)
                self.assertNotEqual(other_parent.span_id,
                                    child_context.span_id)
                self.assertEqual(other_parent.trace_state,
                                 child_context.trace_state)
                self.assertEqual(other_parent.trace_options,
                                 child_context.trace_options)

            # After exiting the child's scope the last span on the stack should
            # become current, not the child's parent.
            self.assertNotEqual(tracer.get_current_span(), other_parent)
            self.assertIs(tracer.get_current_span(), root)
            self.assertIsNotNone(child.end_time)


class TestSpan(unittest.TestCase):

    def test_basic_span(self):
        span = trace.Span('name', mock.Mock(spec=trace_api.SpanContext))
        self.assertEqual(span.name, 'name')
