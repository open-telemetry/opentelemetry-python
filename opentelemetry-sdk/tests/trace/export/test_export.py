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

import multiprocessing
import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from logging import WARNING
from platform import python_implementation, system
from unittest import mock

from pytest import mark

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace
from opentelemetry.sdk.environment_variables import (
    OTEL_BSP_EXPORT_TIMEOUT,
    OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BSP_MAX_QUEUE_SIZE,
    OTEL_BSP_SCHEDULE_DELAY,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export import logger
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class MySpanExporter(export.SpanExporter):
    """Very simple span exporter used for testing."""

    def __init__(
        self,
        destination,
        max_export_batch_size=None,
        export_timeout_millis=0.0,
        export_event: threading.Event = None,
    ):
        self.destination = destination
        self.max_export_batch_size = max_export_batch_size
        self.is_shutdown = False
        self.export_timeout = export_timeout_millis / 1e3
        self.export_event = export_event

    def export(self, spans: trace.Span) -> export.SpanExportResult:
        if (
            self.max_export_batch_size is not None
            and len(spans) > self.max_export_batch_size
        ):
            raise ValueError("Batch is too big")
        time.sleep(self.export_timeout)
        self.destination.extend(span.name for span in spans)
        if self.export_event:
            self.export_event.set()
        return export.SpanExportResult.SUCCESS

    def shutdown(self):
        self.is_shutdown = True


class TestSimpleSpanProcessor(unittest.TestCase):
    def test_simple_span_processor(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.SimpleSpanProcessor(my_exporter)
        tracer_provider.add_span_processor(span_processor)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("xxx"):
                    pass

        self.assertListEqual(["xxx", "bar", "foo"], spans_names_list)

        span_processor.shutdown()
        self.assertTrue(my_exporter.is_shutdown)

    def test_simple_span_processor_no_context(self):
        """Check that we process spans that are never made active.

        SpanProcessors should act on a span's start and end events whether or
        not it is ever the active span.
        """
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.SimpleSpanProcessor(my_exporter)
        tracer_provider.add_span_processor(span_processor)

        with tracer.start_span("foo"):
            with tracer.start_span("bar"):
                with tracer.start_span("xxx"):
                    pass

        self.assertListEqual(["xxx", "bar", "foo"], spans_names_list)

    def test_on_start_accepts_context(self):
        # pylint: disable=no-self-use
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        exporter = MySpanExporter([])
        span_processor = mock.Mock(wraps=export.SimpleSpanProcessor(exporter))
        tracer_provider.add_span_processor(span_processor)

        context = Context()
        span = tracer.start_span("foo", context=context)
        span_processor.on_start.assert_called_once_with(
            span, parent_context=context
        )

    def test_simple_span_processor_not_sampled(self):
        tracer_provider = trace.TracerProvider(
            sampler=trace.sampling.ALWAYS_OFF
        )
        tracer = tracer_provider.get_tracer(__name__)

        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.SimpleSpanProcessor(my_exporter)
        tracer_provider.add_span_processor(span_processor)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("xxx"):
                    pass

        self.assertListEqual([], spans_names_list)


def _create_start_and_end_span(name, span_processor, resource):
    span = trace._Span(
        name,
        trace_api.SpanContext(
            0xDEADBEEF,
            0xDEADBEEF,
            is_remote=False,
            trace_flags=trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED),
        ),
        span_processor=span_processor,
        resource=resource,
    )
    span.start()
    span.end()


class TestBatchSpanProcessor(ConcurrencyTestBase):
    @mock.patch.dict(
        "os.environ",
        {
            OTEL_BSP_MAX_QUEUE_SIZE: "10",
            OTEL_BSP_SCHEDULE_DELAY: "2",
            OTEL_BSP_MAX_EXPORT_BATCH_SIZE: "3",
            OTEL_BSP_EXPORT_TIMEOUT: "4",
        },
    )
    def test_args_env_var(self):
        batch_span_processor = export.BatchSpanProcessor(
            MySpanExporter(destination=[])
        )

        self.assertEqual(batch_span_processor.max_queue_size, 10)
        self.assertEqual(batch_span_processor.schedule_delay_millis, 2)
        self.assertEqual(batch_span_processor.max_export_batch_size, 3)
        self.assertEqual(batch_span_processor.export_timeout_millis, 4)

    def test_args_env_var_defaults(self):
        batch_span_processor = export.BatchSpanProcessor(
            MySpanExporter(destination=[])
        )

        self.assertEqual(batch_span_processor.max_queue_size, 2048)
        self.assertEqual(batch_span_processor.schedule_delay_millis, 5000)
        self.assertEqual(batch_span_processor.max_export_batch_size, 512)
        self.assertEqual(batch_span_processor.export_timeout_millis, 30000)

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_BSP_MAX_QUEUE_SIZE: "a",
            OTEL_BSP_SCHEDULE_DELAY: " ",
            OTEL_BSP_MAX_EXPORT_BATCH_SIZE: "One",
            OTEL_BSP_EXPORT_TIMEOUT: "@",
        },
    )
    def test_args_env_var_value_error(self):
        logger.disabled = True
        batch_span_processor = export.BatchSpanProcessor(
            MySpanExporter(destination=[])
        )
        logger.disabled = False

        self.assertEqual(batch_span_processor.max_queue_size, 2048)
        self.assertEqual(batch_span_processor.schedule_delay_millis, 5000)
        self.assertEqual(batch_span_processor.max_export_batch_size, 512)
        self.assertEqual(batch_span_processor.export_timeout_millis, 30000)

    def test_on_start_accepts_parent_context(self):
        # pylint: disable=no-self-use
        my_exporter = MySpanExporter(destination=[])
        span_processor = mock.Mock(
            wraps=export.BatchSpanProcessor(my_exporter)
        )
        tracer_provider = trace.TracerProvider()
        tracer_provider.add_span_processor(span_processor)
        tracer = tracer_provider.get_tracer(__name__)

        context = Context()
        span = tracer.start_span("foo", context=context)

        span_processor.on_start.assert_called_once_with(
            span, parent_context=context
        )

    def test_shutdown(self):
        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchSpanProcessor(my_exporter)

        span_names = ["xxx", "bar", "foo"]

        resource = Resource.create({})
        for name in span_names:
            _create_start_and_end_span(name, span_processor, resource)

        span_processor.shutdown()
        self.assertTrue(my_exporter.is_shutdown)

        # check that spans are exported without an explicitly call to
        # force_flush()
        self.assertListEqual(span_names, spans_names_list)

    def test_flush(self):
        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchSpanProcessor(my_exporter)

        span_names0 = ["xxx", "bar", "foo"]
        span_names1 = ["yyy", "baz", "fox"]

        resource = Resource.create({})
        for name in span_names0:
            _create_start_and_end_span(name, span_processor, resource)

        self.assertTrue(span_processor.force_flush())
        self.assertListEqual(span_names0, spans_names_list)

        # create some more spans to check that span processor still works
        for name in span_names1:
            _create_start_and_end_span(name, span_processor, resource)

        self.assertTrue(span_processor.force_flush())
        self.assertListEqual(span_names0 + span_names1, spans_names_list)

        span_processor.shutdown()

    def test_flush_empty(self):
        spans_names_list = []

        my_exporter = MySpanExporter(destination=spans_names_list)
        span_processor = export.BatchSpanProcessor(my_exporter)

        self.assertTrue(span_processor.force_flush())

    def test_flush_from_multiple_threads(self):
        num_threads = 50
        num_spans = 10

        span_list = []

        my_exporter = MySpanExporter(destination=span_list)
        span_processor = export.BatchSpanProcessor(
            my_exporter, max_queue_size=512, max_export_batch_size=128
        )

        resource = Resource.create({})

        def create_spans_and_flush(tno: int):
            for span_idx in range(num_spans):
                _create_start_and_end_span(
                    f"Span {tno}-{span_idx}", span_processor, resource
                )
            self.assertTrue(span_processor.force_flush())

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_list = []
            for thread_no in range(num_threads):
                future = executor.submit(create_spans_and_flush, thread_no)
                future_list.append(future)

            executor.shutdown()

        self.assertEqual(num_threads * num_spans, len(span_list))

    def test_flush_timeout(self):
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, export_timeout_millis=500
        )
        span_processor = export.BatchSpanProcessor(my_exporter)

        resource = Resource.create({})
        _create_start_and_end_span("foo", span_processor, resource)

        # check that the timeout is not meet
        with self.assertLogs(level=WARNING):
            self.assertFalse(span_processor.force_flush(100))
        span_processor.shutdown()

    def test_batch_span_processor_lossless(self):
        """Test that no spans are lost when sending max_queue_size spans"""
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, max_export_batch_size=128
        )
        span_processor = export.BatchSpanProcessor(
            my_exporter, max_queue_size=512, max_export_batch_size=128
        )

        resource = Resource.create({})
        for _ in range(512):
            _create_start_and_end_span("foo", span_processor, resource)

        time.sleep(1)
        self.assertTrue(span_processor.force_flush())
        self.assertEqual(len(spans_names_list), 512)
        span_processor.shutdown()

    def test_batch_span_processor_many_spans(self):
        """Test that no spans are lost when sending many spans"""
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, max_export_batch_size=128
        )
        span_processor = export.BatchSpanProcessor(
            my_exporter,
            max_queue_size=256,
            max_export_batch_size=64,
            schedule_delay_millis=100,
        )

        resource = Resource.create({})
        for _ in range(4):
            for _ in range(256):
                _create_start_and_end_span("foo", span_processor, resource)

            time.sleep(0.1)  # give some time for the exporter to upload spans

        self.assertTrue(span_processor.force_flush())
        self.assertEqual(len(spans_names_list), 1024)
        span_processor.shutdown()

    def test_batch_span_processor_not_sampled(self):
        tracer_provider = trace.TracerProvider(
            sampler=trace.sampling.ALWAYS_OFF
        )
        tracer = tracer_provider.get_tracer(__name__)
        spans_names_list = []

        my_exporter = MySpanExporter(
            destination=spans_names_list, max_export_batch_size=128
        )
        span_processor = export.BatchSpanProcessor(
            my_exporter,
            max_queue_size=256,
            max_export_batch_size=64,
            schedule_delay_millis=100,
        )
        tracer_provider.add_span_processor(span_processor)
        with tracer.start_as_current_span("foo"):
            pass
        time.sleep(0.05)  # give some time for the exporter to upload spans

        self.assertTrue(span_processor.force_flush())
        self.assertEqual(len(spans_names_list), 0)
        span_processor.shutdown()

    def _check_fork_trace(self, exporter, expected):
        time.sleep(0.5)  # give some time for the exporter to upload spans
        spans = exporter.get_finished_spans()
        for span in spans:
            self.assertIn(span.name, expected)

    @unittest.skipUnless(
        hasattr(os, "fork"),
        "needs *nix",
    )
    def test_batch_span_processor_fork(self):
        # pylint: disable=invalid-name
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        exporter = InMemorySpanExporter()
        span_processor = export.BatchSpanProcessor(
            exporter,
            max_queue_size=256,
            max_export_batch_size=64,
            schedule_delay_millis=10,
        )
        tracer_provider.add_span_processor(span_processor)
        with tracer.start_as_current_span("foo"):
            pass
        time.sleep(0.5)  # give some time for the exporter to upload spans

        self.assertTrue(span_processor.force_flush())
        self.assertEqual(len(exporter.get_finished_spans()), 1)
        exporter.clear()

        def child(conn):
            def _target():
                with tracer.start_as_current_span("span") as s:
                    s.set_attribute("i", "1")
                    with tracer.start_as_current_span("temp"):
                        pass

            self.run_with_many_threads(_target, 100)

            time.sleep(0.5)

            spans = exporter.get_finished_spans()
            conn.send(len(spans) == 200)
            conn.close()

        parent_conn, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=child, args=(child_conn,))
        p.start()
        self.assertTrue(parent_conn.recv())
        p.join()

        span_processor.shutdown()

    @mark.skipif(
        python_implementation() == "PyPy" or system() == "Windows",
        reason="This test randomly fails with huge delta in Windows or PyPy",
    )
    def test_batch_span_processor_scheduled_delay(self):
        """Test that spans are exported each schedule_delay_millis"""
        spans_names_list = []

        export_event = threading.Event()
        my_exporter = MySpanExporter(
            destination=spans_names_list, export_event=export_event
        )
        start_time = time.time()
        span_processor = export.BatchSpanProcessor(
            my_exporter,
            schedule_delay_millis=500,
        )

        # create single span
        resource = Resource.create({})
        _create_start_and_end_span("foo", span_processor, resource)

        self.assertTrue(export_event.wait(2))
        export_time = time.time()
        self.assertEqual(len(spans_names_list), 1)
        self.assertAlmostEqual((export_time - start_time) * 1e3, 500, delta=25)

        span_processor.shutdown()

    @mark.skipif(
        python_implementation() == "PyPy" and system() == "Windows",
        reason="This test randomly fails in Windows with PyPy",
    )
    def test_batch_span_processor_reset_timeout(self):
        """Test that the scheduled timeout is reset on cycles without spans"""
        spans_names_list = []

        export_event = threading.Event()
        my_exporter = MySpanExporter(
            destination=spans_names_list,
            export_event=export_event,
            export_timeout_millis=50,
        )

        span_processor = export.BatchSpanProcessor(
            my_exporter,
            schedule_delay_millis=50,
        )

        with mock.patch.object(span_processor.condition, "wait") as mock_wait:
            resource = Resource.create({})
            _create_start_and_end_span("foo", span_processor, resource)
            self.assertTrue(export_event.wait(2))

            # give some time for exporter to loop
            # since wait is mocked it should return immediately
            time.sleep(0.1)
            mock_wait_calls = list(mock_wait.mock_calls)

            # find the index of the call that processed the singular span
            for idx, wait_call in enumerate(mock_wait_calls):
                _, args, __ = wait_call
                if args[0] <= 0:
                    after_calls = mock_wait_calls[idx + 1 :]
                    break

            self.assertTrue(
                all(args[0] >= 0.05 for _, args, __ in after_calls)
            )

        span_processor.shutdown()

    def test_batch_span_processor_parameters(self):
        # zero max_queue_size
        self.assertRaises(
            ValueError, export.BatchSpanProcessor, None, max_queue_size=0
        )

        # negative max_queue_size
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            max_queue_size=-500,
        )

        # zero schedule_delay_millis
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            schedule_delay_millis=0,
        )

        # negative schedule_delay_millis
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            schedule_delay_millis=-500,
        )

        # zero max_export_batch_size
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            max_export_batch_size=0,
        )

        # negative max_export_batch_size
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            max_export_batch_size=-500,
        )

        # max_export_batch_size > max_queue_size:
        self.assertRaises(
            ValueError,
            export.BatchSpanProcessor,
            None,
            max_queue_size=256,
            max_export_batch_size=512,
        )


class TestConsoleSpanExporter(unittest.TestCase):
    def test_export(self):  # pylint: disable=no-self-use
        """Check that the console exporter prints spans."""

        exporter = export.ConsoleSpanExporter()
        # Mocking stdout interferes with debugging and test reporting, mock on
        # the exporter instance instead.
        span = trace._Span("span name", trace_api.INVALID_SPAN_CONTEXT)
        with mock.patch.object(exporter, "out") as mock_stdout:
            exporter.export([span])
        mock_stdout.write.assert_called_once_with(span.to_json() + os.linesep)

        self.assertEqual(mock_stdout.write.call_count, 1)
        self.assertEqual(mock_stdout.flush.call_count, 1)

    def test_export_custom(self):  # pylint: disable=no-self-use
        """Check that console exporter uses custom io, formatter."""
        mock_span_str = mock.Mock(str)

        def formatter(span):  # pylint: disable=unused-argument
            return mock_span_str

        mock_stdout = mock.Mock()
        exporter = export.ConsoleSpanExporter(
            out=mock_stdout, formatter=formatter
        )
        exporter.export([trace._Span("span name", mock.Mock())])
        mock_stdout.write.assert_called_once_with(mock_span_str)
