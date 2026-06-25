# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class TestNonFiniteMeasurements(TestCase):
    """Verify non-finite values (NaN, Inf) are dropped before aggregation
    and do not corrupt exported metric data."""

    def setUp(self):
        self.reader = InMemoryMetricReader()
        self.provider = MeterProvider(
            resource=Resource.create({SERVICE_NAME: "otel-test"}),
            metric_readers=[self.reader],
        )
        self.meter = self.provider.get_meter("test-meter")

    def tearDown(self):
        self.provider.shutdown()

    def _get_data_point(self, metric_name):
        metrics = self.reader.get_metrics_data()
        for rm in metrics.resource_metrics:
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    if m.name == metric_name:
                        return m.data.data_points[0]
        return None

    def test_counter_nan_does_not_corrupt_sum(self):
        counter = self.meter.create_counter("c_nan")
        counter.add(5)
        counter.add(float("nan"))
        counter.add(3)
        dp = self._get_data_point("c_nan")
        self.assertIsNotNone(dp)
        self.assertEqual(dp.value, 8)

    def test_counter_inf_does_not_corrupt_sum(self):
        counter = self.meter.create_counter("c_inf")
        counter.add(5)
        counter.add(float("inf"))
        counter.add(3)
        dp = self._get_data_point("c_inf")
        self.assertIsNotNone(dp)
        self.assertEqual(dp.value, 8)

    def test_histogram_nan_does_not_corrupt_count_or_sum(self):
        hist = self.meter.create_histogram("h_nan")
        hist.record(10)
        hist.record(float("nan"))
        hist.record(20)
        dp = self._get_data_point("h_nan")
        self.assertIsNotNone(dp)
        self.assertEqual(dp.count, 2)
        self.assertEqual(dp.sum, 30)

    def test_histogram_inf_does_not_corrupt_count_or_sum(self):
        hist = self.meter.create_histogram("h_inf")
        hist.record(10)
        hist.record(float("inf"))
        hist.record(20)
        dp = self._get_data_point("h_inf")
        self.assertIsNotNone(dp)
        self.assertEqual(dp.count, 2)
        self.assertEqual(dp.sum, 30)

    def test_updown_counter_nan_does_not_corrupt_sum(self):
        udc = self.meter.create_up_down_counter("udc_nan")
        udc.add(10)
        udc.add(float("nan"))
        udc.add(-3)
        dp = self._get_data_point("udc_nan")
        self.assertIsNotNone(dp)
        self.assertEqual(dp.value, 7)
