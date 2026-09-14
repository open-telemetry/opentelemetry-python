# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.metrics._internal import _ProxyMeterProvider
from opentelemetry.sdk._shared_internal._processor_metrics import (
    ProcessorMetrics,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)


class TestProcessorMetrics(TestCase):
    def test_queue_capacity_with_late_meter_provider(self):
        cases = (
            (
                "traces",
                OtelComponentTypeValues.BATCHING_SPAN_PROCESSOR,
                "otel.sdk.processor.span.queue.capacity",
            ),
            (
                "logs",
                OtelComponentTypeValues.BATCHING_LOG_PROCESSOR,
                "otel.sdk.processor.log.queue.capacity",
            ),
        )

        for signal, component_type, metric_name in cases:
            with self.subTest(signal=signal):
                proxy_meter_provider = _ProxyMeterProvider()
                ProcessorMetrics(
                    signal,
                    component_type,
                    proxy_meter_provider,
                    capacity=2048,
                )

                metric_reader = InMemoryMetricReader()
                meter_provider = MeterProvider(metric_readers=[metric_reader])
                proxy_meter_provider.on_set_meter_provider(meter_provider)

                for _ in range(2):
                    metric_data = metric_reader.get_metrics_data()
                    metrics = metric_data.resource_metrics[0].scope_metrics[0].metrics
                    queue_capacity = next(metric for metric in metrics if metric.name == metric_name)
                    self.assertEqual(
                        queue_capacity.data.data_points[0].value,
                        2048,
                    )

                meter_provider.shutdown()
