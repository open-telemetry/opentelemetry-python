# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import DropAggregation, View


class TestDisableDefaultViews(TestCase):
    def test_disable_default_views(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[View(instrument_name="*", aggregation=DropAggregation())],
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        counter.add(10, {"label": "value1"})
        counter.add(10, {"label": "value2"})
        counter.add(10, {"label": "value3"})
        self.assertIsNone(reader.get_metrics_data())

    def test_disable_default_views_add_custom(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(instrument_name="*", aggregation=DropAggregation()),
                View(instrument_name="testhist"),
            ],
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        histogram = meter.create_histogram("testhist")
        counter.add(10, {"label": "value1"})
        counter.add(10, {"label": "value2"})
        counter.add(10, {"label": "value3"})
        histogram.record(12, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        self.assertEqual(
            metrics.resource_metrics[0].scope_metrics[0].metrics[0].name,
            "testhist",
        )
