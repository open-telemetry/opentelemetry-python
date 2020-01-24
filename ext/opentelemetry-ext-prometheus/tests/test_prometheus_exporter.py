# Copyright 2020, OpenTelemetry Authors
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

import unittest
from unittest import mock

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    UnknownMetricFamily,
)

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    Aggregator,
    CounterAggregator,
)
from opentelemetry.ext.prometheus import (
    PrometheusMetricsExporter,
    CustomCollector,
    sanitize,
)


class TestPrometheusMetricExporter(unittest.TestCase):
    def setUp(self):
        self._meter = metrics.Meter()
        self._test_metric = self._meter.create_metric(
            "testname",
            "testdesc",
            "unit",
            int,
            metrics.Counter,
            ["environment"],
        )
        kvp = {"environment": "staging"}
        self._test_label_set = self._meter.get_label_set(kvp)

        self._mock_start_http_server = mock.Mock()
        self._start_http_server_patch = mock.patch(
            "prometheus_client.exposition._ThreadingSimpleServer",
            side_effect=self._mock_start_http_server,
        )
        self._mock_registry_register = mock.Mock()
        self._registry_register_patch = mock.patch(
            "prometheus_client.core.REGISTRY.register",
            side_effect=self._mock_registry_register,
        )

    def test_constructor(self):
        """Test the constructor."""
        with self._registry_register_patch, self._start_http_server_patch:
            exporter = PrometheusMetricsExporter(
                1234, "testaddress", "testprefix"
            )
            self.assertEqual(exporter._port, 1234)
            self.assertEqual(exporter._address, "testaddress")
            self.assertEqual(exporter._collector._prefix, "testprefix")
            self.assertTrue(self._mock_start_http_server.called)
            self.assertTrue(self._mock_registry_register.called)

    def test_shutdown(self):
        with mock.patch(
            "prometheus_client.core.REGISTRY.unregister"
        ) as registry_unregister_patch, self._start_http_server_patch:
            exporter = PrometheusMetricsExporter()
            exporter.shutdown()
            self.assertTrue(registry_unregister_patch.called)

    def test_export(self):
        with self._registry_register_patch, self._start_http_server_patch:
            record = MetricRecord(
                CounterAggregator(), self._test_label_set, self._test_metric
            )
            exporter = PrometheusMetricsExporter()
            result = exporter.export([record])
            self.assertEqual(len(exporter._collector._metrics_to_export), 1)
            self.assertIs(result, MetricsExportResult.SUCCESS)

    def test_counter_to_prometheus(self):
        meter = metrics.Meter()
        metric = meter.create_metric(
            "test@name",
            "testdesc",
            "unit",
            int,
            metrics.Counter,
            ["environment"],
        )
        kvp = {"environment": "staging"}
        label_set = meter.get_label_set(kvp)
        aggregator = CounterAggregator()
        aggregator.check_point = 123
        record = MetricRecord(aggregator, label_set, metric)
        collector = CustomCollector("testprefix")
        collector.add_metrics_data([record])

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(prometheus_metric.name, "testprefix_test_name")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment"], "staging"
            )

    def test_gauge_to_prometheus(self):
        # TODO: Add unit test once GaugeAggregator is available
        self.assertEqual(True, True)

    def test_measure_to_prometheus(self):
        # TODO: Add unit test once Measure Aggregators are available
        self.assertEqual(True, True)