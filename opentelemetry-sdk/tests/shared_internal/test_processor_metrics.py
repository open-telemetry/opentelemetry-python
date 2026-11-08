# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.metrics._internal import _ProxyMeterProvider
from opentelemetry.sdk._shared_internal._processor_metrics import ProcessorMetrics
from opentelemetry.sdk.metrics import MeterProvider, ObservableUpDownCounter
from opentelemetry.sdk.metrics.export import AggregationTemporality, InMemoryMetricReader
from opentelemetry.semconv._incubating.attributes.otel_attributes import OtelComponentTypeValues


class TestProcessorMetrics(TestCase):
    def test_queue_capacity_is_replayed_when_proxy_provider_is_replaced(self):
        reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[reader])
        proxy_provider = _ProxyMeterProvider()
        try:
            ProcessorMetrics(
                "traces",
                OtelComponentTypeValues.BATCHING_SPAN_PROCESSOR,
                proxy_provider,
                capacity=42,
            )
            proxy_provider.on_set_meter_provider(provider)

            metrics_data = reader.get_metrics_data()
            metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
            queue_capacity = next(
                metric for metric in metrics if metric.name == "otel.sdk.processor.span.queue.capacity"
            )
            self.assertEqual(queue_capacity.data.data_points[0].value, 42)
        finally:
            provider.shutdown()

    def test_queue_capacity_is_reported_on_every_delta_collection(self):
        reader = InMemoryMetricReader(
            preferred_temporality={ObservableUpDownCounter: AggregationTemporality.DELTA}
        )
        provider = MeterProvider(metric_readers=[reader])
        try:
            ProcessorMetrics(
                "traces",
                OtelComponentTypeValues.BATCHING_SPAN_PROCESSOR,
                provider,
                capacity=42,
            )

            for expected_value in (42, 0):
                metrics_data = reader.get_metrics_data()
                metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
                queue_capacity = next(
                    metric for metric in metrics if metric.name == "otel.sdk.processor.span.queue.capacity"
                )
                self.assertEqual(queue_capacity.data.data_points[0].value, expected_value)
        finally:
            provider.shutdown()
