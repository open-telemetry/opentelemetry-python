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

import unittest
from unittest import mock

from opentelemetry.exporter.prometheus_remote_write import (
    TimeSeriesData,
    Config,
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    ValueObserverAggregator,
    LastValueAggregator,
    HistogramAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
)
from opentelemetry.sdk.util import get_dict_as_key

class TestPrometheusRemoteWriteMetricExporter(unittest.TestCase):
    def setUp(self):
        set_meter_provider(metrics.MeterProvider())
        self._test_config = Config({
            "url": "https://testurl.com",
            "name": "test_name",
            "remote_timeout": "30s",
        })
        self._meter = get_meter_provider().get_meter(__name__)
        self._test_metric = self._meter.create_counter(
            "testname", "testdesc", "unit", int,
        )
        labels = {"environment": "staging"}
        self._labels_key = get_dict_as_key(labels)

    def test_export(self):
        record = MetricRecord(
            self._test_metric,
            self._labels_key,
            SumAggregator(),
            get_meter_provider().resource,
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        result = exporter.export([record])
        self.assertIs(result, MetricsExportResult.SUCCESS)
    
    def test_convert_from_sum(self):
        sum_record = MetricRecord(
            self._test_metric,
            self._labels_key,
            SumAggregator(),
            get_meter_provider().resource,
        )
        sum_record.aggregator.update(5)
        expected_timeseries = TimeSeriesData(["testname"], [5])
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_sum(sum_record)
        self.assertEqual(timeseries, expected_timeseries)
    
