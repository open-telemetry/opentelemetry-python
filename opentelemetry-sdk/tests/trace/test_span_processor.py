# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import abc
import gc
import multiprocessing
import os
import time
import unittest
import weakref
from threading import Event, Thread
from unittest import mock

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


def span_event_start_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":start"


def span_event_ending_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":ending"


def span_event_end_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":end"


class MySpanProcessor(trace.SpanProcessor):
    def __init__(self, name, span_list):
        self.name = name
        self.span_list = span_list

    def on_start(self, span: "trace.Span", parent_context: Context | None = None) -> None:
        self.span_list.append(span_event_start_fmt(self.name, span.name))

    def on_end(self, span: "trace.Span") -> None:
        self.span_list.append(span_event_end_fmt(self.name, span.name))


class MyExtendedSpanProcessor(MySpanProcessor):
    def _on_ending(self, span: "trace.Span") -> None:
        self.span_list.append(span_event_ending_fmt(self.name, span.name))


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

    # pylint: disable=too-many-statements
    def test_span_processor_with_on_ending(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp1 = MyExtendedSpanProcessor("SP1", spans_calls_list)
        sp2 = MyExtendedSpanProcessor("SP2", spans_calls_list)

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

                expected_list.append(span_event_ending_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_ending_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_ending_fmt("SP1", "foo"))
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

                expected_list.append(span_event_ending_fmt("SP1", "baz"))
                expected_list.append(span_event_ending_fmt("SP2", "baz"))
                expected_list.append(span_event_end_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP2", "baz"))

            expected_list.append(span_event_ending_fmt("SP1", "bar"))
            expected_list.append(span_event_ending_fmt("SP2", "bar"))
            expected_list.append(span_event_end_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP2", "bar"))

        expected_list.append(span_event_ending_fmt("SP1", "foo"))
        expected_list.append(span_event_ending_fmt("SP2", "foo"))
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

    def test_on_ending_not_implemented_does_not_raise(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Does not implement _on_ending
        sp = MySpanProcessor("SP1", spans_calls_list)
        tracer_provider.add_span_processor(sp)

        try:
            with tracer.start_as_current_span("foo"):
                expected_list.append(span_event_start_fmt("SP1", "foo"))

                with tracer.start_as_current_span("bar"):
                    expected_list.append(span_event_start_fmt("SP1", "bar"))

                    with tracer.start_as_current_span("baz"):
                        expected_list.append(span_event_start_fmt("SP1", "baz"))

                    expected_list.append(span_event_end_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP1", "foo"))
        except NotImplementedError:
            self.fail("_on_ending() should not raise an exception")

        self.assertListEqual(spans_calls_list, expected_list)

    def test_span_mutable_during_on_ending(self):
        exporter = InMemorySpanExporter()

        class MutatingSpanProcessor(trace.SpanProcessor):
            def _on_ending(self, span: "trace.Span") -> None:
                assert span.is_recording()
                assert span.end_time is not None
                span.update_name("renamed")
                span.set_attribute("attribute", "value")
                span.set_attributes({"attributes": "value"})
                span.add_event("event")
                span.add_link(
                    trace_api.SpanContext(
                        trace_id=0x1,
                        span_id=0x2,
                        is_remote=False,
                    )
                )
                span.set_status(trace_api.StatusCode.ERROR)

        tracer_provider = trace.TracerProvider()
        tracer_provider.add_span_processor(MutatingSpanProcessor())
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer(__name__)

        tracer.start_span("foo").end()

        (span,) = exporter.get_finished_spans()
        self.assertEqual(span.name, "renamed")
        self.assertEqual(span.attributes["attribute"], "value")
        self.assertEqual(span.attributes["attributes"], "value")
        self.assertEqual(span.events[0].name, "event")
        self.assertEqual(len(span.links), 1)
        self.assertIs(span.status.status_code, trace_api.StatusCode.ERROR)

    def test_end_during_on_ending_is_ignored(self):
        exporter = InMemorySpanExporter()
        on_ending_calls = []

        class ReentrantSpanProcessor(trace.SpanProcessor):
            def _on_ending(self, span: "trace.Span") -> None:
                on_ending_calls.append(span)
                span.end()

        tracer_provider = trace.TracerProvider()
        tracer_provider.add_span_processor(ReentrantSpanProcessor())
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer(__name__)

        span = tracer.start_span("foo")
        span.end()

        self.assertEqual(len(on_ending_calls), 1)
        self.assertEqual(len(exporter.get_finished_spans()), 1)

        # After end() returns the span is immutable again.
        self.assertFalse(span.is_recording())
        span.set_attribute("late", "value")
        (exported,) = exporter.get_finished_spans()
        self.assertNotIn("late", exported.attributes)

    def test_other_thread_cannot_mutate_during_on_ending(self):
        exporter = InMemorySpanExporter()
        inside_on_ending = Event()
        other_thread_done = Event()

        class BlockingSpanProcessor(trace.SpanProcessor):
            def _on_ending(self, span: "trace.Span") -> None:
                inside_on_ending.set()
                other_thread_done.wait(5)

        tracer_provider = trace.TracerProvider()
        tracer_provider.add_span_processor(BlockingSpanProcessor())
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        span = tracer_provider.get_tracer(__name__).start_span("foo")

        def mutate_from_another_thread():
            inside_on_ending.wait(5)
            span.set_attribute("other.attribute", "value")
            span.set_attributes({"other.attributes": "value"})
            span.update_name("renamed")
            span.add_event("event")
            span.add_link(
                trace_api.SpanContext(
                    trace_id=0x1,
                    span_id=0x2,
                    is_remote=False,
                )
            )
            span.set_status(trace_api.StatusCode.ERROR)
            other_thread_done.set()

        thread = Thread(target=mutate_from_another_thread)
        thread.start()
        span.end()
        thread.join(5)

        self.assertTrue(inside_on_ending.is_set())
        self.assertTrue(other_thread_done.is_set())

        (exported,) = exporter.get_finished_spans()
        self.assertNotIn("other.attribute", exported.attributes)
        self.assertNotIn("other.attributes", exported.attributes)
        self.assertEqual(exported.name, "foo")
        self.assertEqual(len(exported.events), 0)
        self.assertEqual(len(exported.links), 0)
        self.assertIs(exported.status.status_code, trace_api.StatusCode.UNSET)

    def test_other_thread_does_not_see_span_recording_during_on_ending(self):
        inside_on_ending = Event()
        other_thread_done = Event()
        recording_seen_by_other_thread = []

        class BlockingSpanProcessor(trace.SpanProcessor):
            def _on_ending(self, span: "trace.Span") -> None:
                inside_on_ending.set()
                other_thread_done.wait(5)

        tracer_provider = trace.TracerProvider()
        tracer_provider.add_span_processor(BlockingSpanProcessor())
        span = tracer_provider.get_tracer(__name__).start_span("foo")

        def observe_from_another_thread():
            inside_on_ending.wait(5)
            recording_seen_by_other_thread.append(span.is_recording())
            other_thread_done.set()

        thread = Thread(target=observe_from_another_thread)
        thread.start()
        span.end()
        thread.join(5)

        self.assertTrue(other_thread_done.is_set())
        self.assertEqual(recording_seen_by_other_thread, [False])

    def test_span_is_frozen_when_record_end_metrics_raises(self):
        def record_end_metrics_that_raises():
            raise RuntimeError("meter blew up")

        tracer_provider = trace.TracerProvider()
        span = tracer_provider.get_tracer(__name__).start_span("foo")
        # pylint: disable=protected-access
        span._record_end_metrics = record_end_metrics_that_raises

        with self.assertRaises(RuntimeError):
            span.end()

        self.assertFalse(span.is_recording())
        span.set_attribute("late", "value")
        self.assertNotIn("late", span.attributes)


class MultiSpanProcessorTestBase(abc.ABC):
    @abc.abstractmethod
    def create_multi_span_processor(
        self,
    ) -> trace.SynchronousMultiSpanProcessor | trace.ConcurrentMultiSpanProcessor:
        pass

    @staticmethod
    def create_default_span() -> trace_api.Span:
        span_context = trace_api.SpanContext(37, 73, is_remote=False)
        return trace_api.NonRecordingSpan(span_context)

    def test_on_start(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        span = self.create_default_span()
        context = Context()
        multi_processor.on_start(span, parent_context=context)

        for mock_processor in mocks:
            mock_processor.on_start.assert_called_once_with(span, parent_context=context)
        multi_processor.shutdown()

    def test_on_ending(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        span = self.create_default_span()
        # pylint: disable=protected-access
        multi_processor._on_ending(span)

        for mock_processor in mocks:
            # pylint: disable=protected-access
            mock_processor._on_ending.assert_called_once_with(span)
        multi_processor.shutdown()

    def test_on_end(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        span = self.create_default_span()
        multi_processor.on_end(span)

        for mock_processor in mocks:
            mock_processor.on_end.assert_called_once_with(span)
        multi_processor.shutdown()

    def test_on_shutdown(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(5)]
        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        multi_processor.shutdown()

        for mock_processor in mocks:
            mock_processor.shutdown.assert_called_once_with()

    def test_force_flush(self):
        multi_processor = self.create_multi_span_processor()

        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(5)]
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

    def test_on_ending_not_implemented_does_not_raise(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        multi_processor = self.create_multi_span_processor()
        # Does not implement _on_ending
        multi_processor.add_span_processor(MySpanProcessor("SP1", spans_calls_list))

        tracer_provider.add_span_processor(multi_processor)

        try:
            with tracer.start_as_current_span("foo"):
                expected_list.append(span_event_start_fmt("SP1", "foo"))

                with tracer.start_as_current_span("bar"):
                    expected_list.append(span_event_start_fmt("SP1", "bar"))

                    with tracer.start_as_current_span("baz"):
                        expected_list.append(span_event_start_fmt("SP1", "baz"))

                    expected_list.append(span_event_end_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP1", "foo"))
        except NotImplementedError:
            # pylint: disable=no-member
            self.fail("_on_ending() should not raise an exception")

        # pylint: disable=no-member
        self.assertListEqual(spans_calls_list, expected_list)

    def test_span_mutable_during_on_ending(self):
        multi_processor = self.create_multi_span_processor()
        exporter = InMemorySpanExporter()

        class MutatingSpanProcessor(trace.SpanProcessor):
            def _on_ending(self, span: "trace.Span") -> None:
                span.set_attribute("attribute", "value")

        multi_processor.add_span_processor(MutatingSpanProcessor())
        multi_processor.add_span_processor(SimpleSpanProcessor(exporter))
        tracer_provider = trace.TracerProvider(active_span_processor=multi_processor)

        tracer_provider.get_tracer(__name__).start_span("foo").end()

        (span,) = exporter.get_finished_spans()
        # pylint: disable=no-member
        self.assertEqual(span.attributes["attribute"], "value")
        multi_processor.shutdown()


class TestSynchronousMultiSpanProcessor(MultiSpanProcessorTestBase, unittest.TestCase):
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
        self.assertEqual(1, mock_processor2.force_flush.call_count)

    def test_force_flush_processor_returns_none(self):
        multi_processor = trace.SynchronousMultiSpanProcessor()

        mock_processor1 = mock.Mock(spec=trace.SpanProcessor)
        mock_processor1.force_flush = mock.Mock(return_value=None)
        multi_processor.add_span_processor(mock_processor1)
        mock_processor2 = mock.Mock(spec=trace.SpanProcessor)
        mock_processor2.force_flush = mock.Mock(return_value=True)
        multi_processor.add_span_processor(mock_processor2)

        flushed = multi_processor.force_flush(50)
        self.assertTrue(flushed)
        self.assertEqual(1, mock_processor1.force_flush.call_count)
        self.assertEqual(1, mock_processor2.force_flush.call_count)

    def test_force_flush_default_processor(self):
        multi_processor = trace.SynchronousMultiSpanProcessor()

        default_processor = trace.SpanProcessor()
        multi_processor.add_span_processor(default_processor)
        mock_processor = mock.Mock(spec=trace.SpanProcessor)
        mock_processor.force_flush = mock.Mock(return_value=True)
        multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush(50)
        self.assertTrue(flushed)
        self.assertEqual(1, mock_processor.force_flush.call_count)


class TestConcurrentMultiSpanProcessor(MultiSpanProcessorTestBase, unittest.TestCase):
    def create_multi_span_processor(
        self,
    ) -> trace.ConcurrentMultiSpanProcessor:
        return trace.ConcurrentMultiSpanProcessor(3)

    def test_force_flush_late_by_timeout(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)
        wait_event = Event()

        def delayed_flush(_):
            wait_event.wait()

        late_mock = mock.Mock(spec=trace.SpanProcessor)
        late_mock.force_flush = mock.Mock(side_effect=delayed_flush)
        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(4)]
        mocks.insert(0, late_mock)

        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush(timeout_millis=25)
        # let the thread executing the late_mock continue
        wait_event.set()
        multi_processor.shutdown()

        self.assertFalse(flushed)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)

    def test_force_flush_late_by_span_processor(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)

        late_mock = mock.Mock(spec=trace.SpanProcessor)
        late_mock.force_flush = mock.Mock(return_value=False)
        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(4)]
        mocks.insert(0, late_mock)

        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush()

        self.assertFalse(flushed)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)
        multi_processor.shutdown()

    def test_force_flush_processor_returns_none(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)

        none_mock = mock.Mock(spec=trace.SpanProcessor)
        none_mock.force_flush = mock.Mock(return_value=None)
        mocks = [mock.Mock(spec=trace.SpanProcessor) for _ in range(4)]
        mocks.insert(0, none_mock)

        for mock_processor in mocks:
            multi_processor.add_span_processor(mock_processor)

        flushed = multi_processor.force_flush()

        self.assertTrue(flushed)
        for mock_processor in mocks:
            self.assertEqual(1, mock_processor.force_flush.call_count)
        multi_processor.shutdown()

    def test_processor_gc(self):
        multi_processor = trace.ConcurrentMultiSpanProcessor(5)
        weak_ref = weakref.ref(multi_processor)
        multi_processor.shutdown()

        # When the processor is garbage collected
        del multi_processor
        gc.collect()

        # Then the reference to the processor should no longer exist
        self.assertIsNone(
            weak_ref(),
            "The ConcurrentMultiSpanProcessor object created by this test wasn't garbage collected",
        )

    @unittest.skipUnless(hasattr(os, "fork"), "needs *nix")
    def test_batch_span_processor_fork(self):
        multiprocessing_context = multiprocessing.get_context("fork")
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        exporter = InMemorySpanExporter()
        multi_processor = trace.ConcurrentMultiSpanProcessor(2)
        multi_processor.add_span_processor(SimpleSpanProcessor(exporter))
        tracer_provider.add_span_processor(multi_processor)

        # Use the ConcurrentMultiSpanProcessor in the main process.
        # This is necessary in this test to start using the underlying ThreadPoolExecutor and avoid false positive:
        with tracer.start_as_current_span("main process before fork span"):
            pass
        assert exporter.get_finished_spans()[-1].name == "main process before fork span"

        # The forked ConcurrentMultiSpanProcessor is usable in the child process:
        def child(conn):
            with tracer.start_as_current_span("child process span"):
                pass
            conn.send(exporter.get_finished_spans()[-1].name)
            conn.close()

        parent_conn, child_conn = multiprocessing_context.Pipe()
        process = multiprocessing_context.Process(target=child, args=(child_conn,))
        process.start()
        has_response = parent_conn.poll(timeout=5)
        if not has_response:
            process.kill()
            self.fail("The child process did not send any message after 5 seconds, it's very probably locked")
        process.join(timeout=5)
        assert parent_conn.recv() == "child process span"

        # The ConcurrentMultiSpanProcessor is still usable in the main process after the child process termination:
        with tracer.start_as_current_span("main process after fork span"):
            pass
        assert exporter.get_finished_spans()[-1].name == "main process after fork span"
