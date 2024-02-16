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

import abc
import time
import typing
import unittest
from platform import python_implementation, system
from threading import Event
from typing import Optional
from unittest import mock

from pytest import mark

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace


def span_event_start_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":start"


def span_event_end_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":end"


class MySpanProcessor(trace.SpanProcessor):
    def __init__(self, name, span_list):
        self.name = name
        self.span_list = span_list

    def on_start(
        self, span: "trace.Span", parent_context: Optional[Context] = None
    ) -> None:
        self.span_list.append(span_event_start_fmt(self.name, span.name))

    def on_end(self, span: "trace.Span") -> None:
        self.span_list.append(span_event_end_fmt(self.name, span.name))


class TestSpanProcessor(unittest.TestCase):
    def test_span_processor(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp1 = MySpanProcessor("SP1", spans_calls_list)
        sp2 = MySpanProcessor("SP2", spans_calls_list)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    pass

        # at this point lists must be empty
        self.assertEqual(len(spans_calls_list), 0)

        # add single span processor
        tracer_provider.add_span_processor(sp1)

        with tracer.start_as_current_span("foo"):
            expected_list.append(span_event_start_fmt("SP1", "foo"))

            with tracer.start_as_current_span("bar"):
                expected_list.append(span_event_start_fmt("SP1", "bar"))

                with tracer.start_as_current_span("baz"):
                    expected_list.append(span_event_start_fmt("SP1", "baz"))

                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))

        self.assertListEqual(spans_calls_list, expected_list)

        spans_calls_list.clear()
        expected_list.clear()

        # go for multiple span processors
        tracer_provider.add_span_processor(sp2)

        with tracer.start_as_current_span("foo"):
            expected_list.append(span_event_start_fmt("SP1", "foo"))
            expected_list.append(span_event_start_fmt("SP2", "foo"))

            with tracer.start_as_current_span("bar"):
                expected_list.append(span_event_start_fmt("SP1", "bar"))
                expected_list.append(span_event_start_fmt("SP2", "bar"))

                with tracer.start_as_current_span("baz"):
                    expected_list.append(span_event_start_fmt("SP1", "baz"))
                    expected_list.append(span_event_start_fmt("SP2", "baz"))

                expected_list.append(span_event_end_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP2", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP2", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))
        expected_list.append(span_event_end_fmt("SP2", "foo"))

        # compare if two lists are the same
        self.assertListEqual(spans_calls_list, expected_list)

    def test_add_span_processor_after_span_creation(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp = MySpanProcessor("SP1", spans_calls_list)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    # add span processor after spans have been created
                    tracer_provider.add_span_processor(sp)

                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))

        self.assertListEqual(spans_calls_list, expected_list)


class MultiSpanProcessorTestBase(abc.ABC):
    @abc.abstractmethod
    def create_multi_span_processor(
        self,
    ) -> typing.Union[
        trace.SynchronousMultiSpanProcessor, trace.ConcurrentMultiSpanProcessor
    ]:
        pass

    @staticmethod
    def create_default_span() -> trace_api.Span:
        span_context = trace_api.SpanContext(37, 73, is_remote=False)
        return trace_api.NonRecordingSpan(span_context)

    def test_on_start(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        span = self.create_default_span()
        context = Context()
        multi_processor.on_start(span, parent_context=context)

        for mock_processor in mocks:
            mock_processor.on_start.assert_called_once_with(
                span, parent_context=context
            )
        multi_processor.shutdown()

    def test_on_end(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        span = self.create_default_span()
        multi_processor.on_end(span)

        for mock_processor in mocks:
            mock_processor.on_end.assert_called_once_with(span)
        multi_processor.shutdown()

    def test_on_shutdown(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        multi_processor.shutdown()

        for mock_processor in mocks:
            mock_processor.shutdown.assert_called_once_with()

    def test_force_flush(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)
        timeout_millis = 100

        flushed = multi_processor.force_flush(timeout_millis)

        # pylint: disable=no-member
        self.assertTrue(flushed)
        for mock_processor in mocks:
            # pylint: disable=no-member
            self.assertEqual(1, mock_processor.force_flush.call_count)
        multi_processor.shutdown()


class TestSynchronousMultiSpanProcessor(
    MultiSpanProcessorTestBase, unittest.TestCase
):
    def create_multi_span_processor(
        self,
    ) -> trace.SynchronousMultiSpanProcessor:
        return trace.SynchronousMultiSpanProcessor()

    def test_force_flush_late_by_timeout(self):
        multi_processor = trace.SynchronousMultiSpanProcessor()

        def delayed_flush(_):
            time.sleep(0.055)

        mock_processor1 = mock.Mock(spec=trace.SpanProcessor)
        mock_processor1.force_flush = mock.Mock(side_effect=delayed_flush)
        multi_processor.add_span_processor(mock_processor1)
        mock_processor2 = mock.Mock(spec=trace.SpanProcessor)
        multi_processor.add_span_processor(mock_processor2)

        flushed = multi_processor.force_flush(50)

        self.assertFalse(flushed)
        self.assertEqual(1, mock_processor1.force_flush.call_count)
        self.assertEqual(0, mock_processor2.force_flush.call_count)

    def test_force_flush_late_by_span_processor(self):
        multi_processor = trace.SynchronousMultiSpanProcessor()

        mock_processor1 = mock.Mock(spec=trace.SpanProcessor)
        mock_processor1.force_flush = mock.Mock(return_value=False)
        multi_processor.add_span_processor(mock_processor1)
        mock_processor2 = mock.Mock(spec=trace.SpanProcessor)
        multi_processor.add_span_processor(mock_processor2)

        flushed = multi_processor.force_flush(50)
        self.assertFalse(flushed)
        self.assertEqual(1, mock_processor1.force_flush.call_count)
        self.assertEqual(0, mock_processor2.force_flush.call_count)


class TestConcurrentMultiSpanProcessor(
    MultiSpanProcessorTestBase, unittest.TestCase
):
    def create_multi_span_processor(
        self,
    ) -> trace.ConcurrentMultiSpanProcessor:
        return trace.ConcurrentMultiSpanProcessor(3)

    @mark.skipif(
        python_implementation() == "PyPy" and system() == "Windows",
        reason="This test randomly fails in Windows with PyPy",
    )
    def test_force_flush_late_by_timeout(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)
        wait_event = Event()

        def delayed_flush(_):
            wait_event.wait()

        late_mock = mock.Mock(spec=trace.SpanProcessor)
        late_mock.force_flush = mock.Mock(side_effect=delayed_flush)
        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 4)]
        mocks.insert(0, late_mock)

        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush(timeout_millis=10)
        # let the thread executing the late_mock continue
        wait_event.set()

        self.assertFalse(flushed)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)
        multi_processor.shutdown()

    def test_force_flush_late_by_span_processor(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)

        late_mock = mock.Mock(spec=trace.SpanProcessor)
        late_mock.force_flush = mock.Mock(return_value=False)
        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(0, 4)]
        mocks.insert(0, late_mock)

        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush()

        self.assertFalse(flushed)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)
        multi_processor.shutdown()
