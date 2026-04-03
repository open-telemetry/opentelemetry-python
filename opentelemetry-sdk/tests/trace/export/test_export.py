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
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk import trace
from opentelemetry.sdk.environment_variables import (
    OTEL_BSP_EXPORT_TIMEOUT,
    OTEL_BSP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BSP_MAX_QUEUE_SIZE,
    OTEL_BSP_SCHEDULE_DELAY,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
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

    def test_metrics(self):
        metric_reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        num_exports = 0

        def export_spans(_spans):
            nonlocal num_exports
            num_exports += 1
            if num_exports == 3:
                raise RuntimeError("Export failed")
            return export.SpanExportResult.SUCCESS

        exporter = mock.MagicMock()
        exporter.export.side_effect = export_spans
        span_processor = export.SimpleSpanProcessor(
            exporter, meter_provider=meter_provider
        )
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        tracer_provider.add_span_processor(span_processor)

        with tracer.start_as_current_span("foo"):
            with tracer.start_span("bar"):
                pass
            with tracer.start_span("baz"):
                pass

        metrics_data = metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        self.assertEqual(scope_metrics.scope.name, "opentelemetry-sdk")
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "otel.sdk.processor.span.processed")
        processed_data_points = sorted(
            metrics[0].data.data_points,
            key=lambda dp: dp.attributes.get("error.type", ""),
        )
        self.assertEqual(len(processed_data_points), 2)
        processed_data_point0 = processed_data_points[0]
        self.assertEqual(processed_data_point0.value, 2)
        self.assertEqual(
            processed_data_point0.attributes["otel.component.type"],
            "simple_span_processor",
        )
        self.assertTrue(
            processed_data_point0.attributes["otel.component.name"].startswith(
                "simple_span_processor/"
            )
        )
        self.assertIsNone(processed_data_point0.attributes.get("error.type"))
        processed_data_point1 = processed_data_points[1]
        self.assertEqual(processed_data_point1.value, 1)
        self.assertEqual(
            processed_data_point1.attributes["otel.component.type"],
            "simple_span_processor",
        )
        self.assertTrue(
            processed_data_point1.attributes["otel.component.name"].startswith(
                "simple_span_processor/"
            )
        )
        self.assertEqual(
            processed_data_point1.attributes["error.type"], "RuntimeError"
        )


# Many more test cases for the BatchSpanProcessor exist under
# opentelemetry-sdk/tests/shared_internal/test_batch_processor.py.
# Important: make sure to call .shutdown() on the BatchSpanProcessor
# before the end of the test, otherwise the worker thread will continue
# to run after the end of the test.
class TestBatchSpanProcessor(unittest.TestCase):
    def test_get_span_exporter(self):
        exporter = MySpanExporter(destination=[])
        batch_span_processor = export.BatchSpanProcessor(exporter)
        self.assertEqual(exporter, batch_span_processor.span_exporter)

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

    def test_metrics(self):  # pylint: disable=too-many-locals,too-many-statements
        metric_reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        metric_reader._set_meter_provider(NoOpMeterProvider())
        num_exports = 0
        first_export_event = threading.Event()
        last_export_event = threading.Event()
        run_exports = threading.Event()

        def export_spans(_spans):
            first_export_event.set()
            run_exports.wait()
            nonlocal num_exports
            num_exports += 1
            if num_exports == 3:
                last_export_event.set()
                raise ValueError("Export failed")
            return export.SpanExportResult.SUCCESS

        exporter = mock.MagicMock()
        exporter.export.side_effect = export_spans
        span_processor = export.BatchSpanProcessor(
            exporter,
            meter_provider=meter_provider,
            max_queue_size=1,
            max_export_batch_size=1,
            schedule_delay_millis=1_000_000_000,  # Manually flush
        )
        provider = trace.TracerProvider()
        tracer = provider.get_tracer(__name__)
        provider.add_span_processor(span_processor)

        with tracer.start_as_current_span("foo"):
            pass
        # Wait for span to be sent to exporter
        first_export_event.wait()

        # Queue empty, export in progress, this span is queued
        with tracer.start_as_current_span("bar"):
            pass
        # Queue full, this span is dropped
        with tracer.start_as_current_span("baz"):
            pass

        metrics_data = metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        self.assertEqual(scope_metrics.scope.name, "opentelemetry-sdk")
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 3)
        self.assertEqual(metrics[0].name, "otel.sdk.processor.span.processed")
        processed_data_points = sorted(
            metrics[0].data.data_points,
            key=lambda dp: dp.attributes.get("error.type", ""),
        )
        self.assertEqual(len(processed_data_points), 1)
        processed_data_point0 = processed_data_points[0]
        self.assertEqual(processed_data_point0.value, 1)
        self.assertEqual(
            processed_data_point0.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            processed_data_point0.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )
        self.assertEqual(
            processed_data_point0.attributes.get("error.type"), "queue_full"
        )
        self.assertEqual(
            metrics[1].name, "otel.sdk.processor.span.queue.capacity"
        )
        queue_capacity_data_point = metrics[1].data.data_points[0]
        self.assertEqual(queue_capacity_data_point.value, 1)
        self.assertEqual(
            queue_capacity_data_point.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            queue_capacity_data_point.attributes[
                "otel.component.name"
            ].startswith("batching_span_processor/")
        )
        self.assertEqual(metrics[2].name, "otel.sdk.processor.span.queue.size")
        queue_size_data_point = metrics[2].data.data_points[0]
        self.assertEqual(queue_size_data_point.value, 1)
        self.assertEqual(
            queue_size_data_point.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            queue_size_data_point.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )

        run_exports.set()
        provider.force_flush()

        # This span is processed and exporter returns an error
        with tracer.start_as_current_span("failed"):
            pass
        provider.force_flush()
        last_export_event.wait()

        metrics_data = metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        self.assertEqual(scope_metrics.scope.name, "opentelemetry-sdk")
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 3)
        self.assertEqual(metrics[0].name, "otel.sdk.processor.span.processed")
        processed_data_points = sorted(
            metrics[0].data.data_points,
            key=lambda dp: dp.attributes.get("error.type", ""),
        )
        self.assertEqual(len(processed_data_points), 3)
        processed_data_point0 = processed_data_points[0]
        self.assertEqual(processed_data_point0.value, 2)
        self.assertEqual(
            processed_data_point0.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            processed_data_point0.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )
        self.assertIsNone(processed_data_point0.attributes.get("error.type"))
        processed_data_point1 = processed_data_points[1]
        self.assertEqual(processed_data_point1.value, 1)
        self.assertEqual(
            processed_data_point1.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            processed_data_point1.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )
        self.assertEqual(
            processed_data_point1.attributes.get("error.type"), "ValueError"
        )
        processed_data_point2 = processed_data_points[2]
        self.assertEqual(processed_data_point2.value, 1)
        self.assertEqual(
            processed_data_point2.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            processed_data_point2.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )
        self.assertEqual(
            processed_data_point2.attributes.get("error.type"), "queue_full"
        )
        self.assertEqual(
            metrics[1].name, "otel.sdk.processor.span.queue.capacity"
        )
        queue_capacity_data_point = metrics[1].data.data_points[0]
        self.assertEqual(queue_capacity_data_point.value, 1)
        self.assertEqual(
            queue_capacity_data_point.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            queue_capacity_data_point.attributes[
                "otel.component.name"
            ].startswith("batching_span_processor/")
        )
        self.assertEqual(metrics[2].name, "otel.sdk.processor.span.queue.size")
        queue_size_data_point = metrics[2].data.data_points[0]
        self.assertEqual(queue_size_data_point.value, 0)
        self.assertEqual(
            queue_size_data_point.attributes["otel.component.type"],
            "batching_span_processor",
        )
        self.assertTrue(
            queue_size_data_point.attributes["otel.component.name"].startswith(
                "batching_span_processor/"
            )
        )

        provider.shutdown()


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
