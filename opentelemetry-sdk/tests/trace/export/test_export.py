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


import os
import threading
import time
import unittest
from unittest import mock

from opentelemetry import trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace
from opentelemetry.sdk.environment_variables import (
    OTEL_BSP_EXPORT_TIMEOUT,
    OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BSP_MAX_QUEUE_SIZE,
    OTEL_BSP_SCHEDULE_DELAY,
)
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export import logger

# pylint: disable=protected-access


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


# Many more test cases for the BatchSpanProcessor exist under
# opentelemetry-sdk/tests/shared_internal/test_batch_processor.py.
# Important: make sure to call .shutdown() on the BatchSpanProcessor
# before the end of the test, otherwise the worker thread will continue
# to run after the end of the test.
class TestBatchSpanProcessor(unittest.TestCase):
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

        self.assertEqual(
            batch_span_processor._batch_processor._max_queue_size, 10
        )
        self.assertEqual(
            batch_span_processor._batch_processor._schedule_delay_millis, 2
        )
        self.assertEqual(
            batch_span_processor._batch_processor._max_export_batch_size, 3
        )
        self.assertEqual(
            batch_span_processor._batch_processor._export_timeout_millis, 4
        )
        batch_span_processor.shutdown()

    def test_args_env_var_defaults(self):
        batch_span_processor = export.BatchSpanProcessor(
            MySpanExporter(destination=[])
        )

        self.assertEqual(
            batch_span_processor._batch_processor._max_queue_size, 2048
        )
        self.assertEqual(
            batch_span_processor._batch_processor._schedule_delay_millis, 5000
        )
        self.assertEqual(
            batch_span_processor._batch_processor._max_export_batch_size, 512
        )
        self.assertEqual(
            batch_span_processor._batch_processor._export_timeout_millis, 30000
        )
        batch_span_processor.shutdown()

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

        self.assertEqual(
            batch_span_processor._batch_processor._max_queue_size, 2048
        )
        self.assertEqual(
            batch_span_processor._batch_processor._schedule_delay_millis, 5000
        )
        self.assertEqual(
            batch_span_processor._batch_processor._max_export_batch_size, 512
        )
        self.assertEqual(
            batch_span_processor._batch_processor._export_timeout_millis, 30000
        )
        batch_span_processor.shutdown()

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

        span_processor.force_flush()
        self.assertEqual(len(spans_names_list), 0)
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
