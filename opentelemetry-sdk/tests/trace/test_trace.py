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
import unittest

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace


class TestTracer(unittest.TestCase):

    def test_extends_api(self):
        tracer = trace.Tracer()
        self.assertIsInstance(tracer, trace_api.Tracer)


class TestSpanCreation(unittest.TestCase):

    def test_start_span_implicit(self):
        tracer = trace.Tracer('test_start_span_implicit')

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
        tracer = trace.Tracer('test_start_span_explicit')

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

    def test_span_members(self):
        tracer = trace.Tracer('test_span_members')

        other_context1 = trace_api.SpanContext(
            trace_id=trace.generate_trace_id(),
            span_id=trace.generate_span_id()
        )
        other_context2 = trace_api.SpanContext(
            trace_id=trace.generate_trace_id(),
            span_id=trace.generate_span_id()
        )

        self.assertIsNone(tracer.get_current_span())

        with tracer.start_span('root') as root:
            root.set_attribute('component', 'http')
            root.set_attribute('http.method', 'GET')
            root.set_attribute('http.url',
                               'https://example.com:779/path/12/?q=d#123')
            root.set_attribute('http.status_code', 200)
            root.set_attribute('http.status_text', 'OK')
            root.set_attribute('misc.pi', 3.14)

            # Setting an attribute with the same key as an existing attribute
            # SHOULD overwrite the existing attribute's value.
            root.set_attribute('attr-key', 'attr-value1')
            root.set_attribute('attr-key', 'attr-value2')

            root.add_event('event0')
            root.add_event('event1', {'name': 'birthday'})

            root.add_link(other_context1)
            root.add_link(other_context2, {'name': 'neighbor'})

            root.update_name('toor')
            self.assertEqual(root.name, 'toor')

            # The public API does not expose getters.
            # Checks by accessing the span members directly

            self.assertEqual(len(root.attributes), 7)
            self.assertEqual(root.attributes['component'], 'http')
            self.assertEqual(root.attributes['http.method'], 'GET')
            self.assertEqual(root.attributes['http.url'],
                             'https://example.com:779/path/12/?q=d#123')
            self.assertEqual(root.attributes['http.status_code'], 200)
            self.assertEqual(root.attributes['http.status_text'], 'OK')
            self.assertEqual(root.attributes['misc.pi'], 3.14)
            self.assertEqual(root.attributes['attr-key'], 'attr-value2')

            self.assertEqual(len(root.events), 2)
            self.assertEqual(root.events[0],
                             trace.Event(name='event0',
                                         attributes={}))
            self.assertEqual(root.events[1],
                             trace.Event(name='event1',
                                         attributes={'name': 'birthday'}))

            self.assertEqual(len(root.links), 2)
            self.assertEqual(root.links[0].context.trace_id,
                             other_context1.trace_id)
            self.assertEqual(root.links[0].context.span_id,
                             other_context1.span_id)
            self.assertEqual(root.links[0].attributes, {})
            self.assertEqual(root.links[1].context.trace_id,
                             other_context2.trace_id)
            self.assertEqual(root.links[1].context.span_id,
                             other_context2.span_id)
            self.assertEqual(root.links[1].attributes, {'name': 'neighbor'})


class TestSpan(unittest.TestCase):

    def test_basic_span(self):
        span = trace.Span('name', mock.Mock(spec=trace_api.SpanContext))
        self.assertEqual(span.name, 'name')
