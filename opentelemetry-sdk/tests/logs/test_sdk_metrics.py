# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader


class TestLoggerProviderMetrics(TestCase):
    def setUp(self):
        self.metric_reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.metric_reader]
        )

    def tearDown(self):
        self.meter_provider.shutdown()

    def assert_created_logs(self, metric_data, value, attrs):
        metrics = metric_data.resource_metrics[0].scope_metrics[0].metrics
        created_logs_metric = next(
            (m for m in metrics if m.name == "otel.sdk.log.created"), None
        )
        self.assertIsNotNone(created_logs_metric)
        self.assertEqual(created_logs_metric.data.data_points[0].value, value)
        self.assertDictEqual(
            created_logs_metric.data.data_points[0].attributes, attrs
        )

    def test_create_logs(self):
        logger_provider = LoggerProvider(meter_provider=self.meter_provider)
        logger = logger_provider.get_logger("test")
        logger.emit(body="log1")
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_created_logs(
            metric_data,
            1,
            {},
        )
        logger.emit(body="log2")
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_created_logs(
            metric_data,
            2,
            {},
        )
