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

from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader


@patch.dict("os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: "true"})
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


class TestLoggerProviderMetricsDisabled(TestCase):
    def test_disabled_by_default(self):
        metric_reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        logger_provider = LoggerProvider(meter_provider=meter_provider)
        logger = logger_provider.get_logger("test")

        logger.emit(body="log1")

        self.assertIsNone(metric_reader.get_metrics_data())
        meter_provider.shutdown()
