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
import time
from unittest.mock import MagicMock, patch

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    UnknownMetricFamily,
)

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator
from opentelemetry.ext.prometheus import (
    PrometheusMetricsExporter,
    CustomCollector,
    sanitize,
)


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestPrometheusMetricExporter(unittest.TestCase):
    def test_constructor(self):
        """Test the constructor."""
        port = 8000
        address = "localhost"
        meter = metrics.Meter()
        metric = meter.create_metric(
            "testname",
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
        exporter = PrometheusMetricsExporter(port=port, address=address)

        exporter.export([record])

        # Prevent main from exiting to see the data on prometheus
        # localhost:8000/metrics
        while True:
            pass

    def test_shutdown(self):
        exporter = PrometheusMetricsExporter()

    def test_export(self):
        exporter = PrometheusMetricsExporter()

    def test_counter_to_prometheus(self):
        meter = metrics.Meter()
        metric = meter.create_metric(
            "testname",
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
        collector = CustomCollector()
        collector.add_metrics_data([record])

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(prometheus_metric.name, "testname")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment"], "staging"
            )
