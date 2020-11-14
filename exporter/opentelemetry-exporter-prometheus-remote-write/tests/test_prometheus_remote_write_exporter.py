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
    Config,
    PrometheusRemoteWriteMetricsExporter,
    TimeSeriesData,
)
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import (
    HistogramAggregator,
    LastValueAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.util import get_dict_as_key


class TestPrometheusRemoteWriteMetricExporter(unittest.TestCase):
    # Initializes test data that is reused across tests
    def setUp(self):
        set_meter_provider(metrics.MeterProvider())
        self._test_config = Config(endpoint="/prom/test_endpoint")
        self._meter = get_meter_provider().get_meter(__name__)
        self._test_metric = self._meter.create_counter(
            "testname",
            "testdesc",
            "unit",
            int,
        )
        labels = {"environment": "staging"}
        self._labels_key = get_dict_as_key(labels)

    # Ensures export is successful with valid metric_records and config
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

    # Ensures sum aggregator is correctly converted to timeseries
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

    # Ensures sum min_max_count aggregator is correctly converted to timeseries
    def test_convert_from_min_max_sum_count(self):
        min_max_sum_count_record = MetricRecord(
            self._test_metric,
            self._labels_key,
            MinMaxSumCountAggregator(),
            get_meter_provider().resource,
        )
        min_max_sum_count_record.aggregator.update(5)
        expected_timeseries = TimeSeriesData(
            ["testname_min", "testname_max", "testname_sum", "testname_count"],
            [5, 5, 5, 1],
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_min_max_sum_count(
            min_max_sum_count_record
        )
        self.assertEqual(timeseries, expected_timeseries)

    # Ensures histogram aggregator is correctly converted to timeseries
    def test_convert_from_histogram(self):
        histogram_record = MetricRecord(
            self._test_metric,
            self._labels_key,
            HistogramAggregator(),
            get_meter_provider().resource,
        )
        histogram_record.aggregator.update(5)
        expected_timeseries = TimeSeriesData(
            [
                "testname_count",
                "testname_sum",
                'testname_{le="0"}',
                'testname_{le="+Inf"}',
            ],
            [1, 5, 0, 1],
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_histogram(histogram_record)
        self.assertEqual(timeseries, expected_timeseries)

    # Ensures last value aggregator is correctly converted to timeseries
    def test_convert_from_last_value(self):
        last_value_record = MetricRecord(
            self._test_metric,
            self._labels_key,
            LastValueAggregator(),
            get_meter_provider().resource,
        )
        last_value_record.aggregator.update(5)
        expected_timeseries = TimeSeriesData(["testname"], [5])
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_last_value(last_value_record)
        self.assertEqual(timeseries, expected_timeseries)

    # Ensures value observer aggregator is correctly converted to timeseries
    def test_convert_from_value_observer(self):
        value_observer_record = MetricRecord(
            self._test_metric,
            self._labels_key,
            ValueObserverAggregator(),
            get_meter_provider().resource,
        )
        value_observer_record.aggregator.update(5)
        expected_timeseries = TimeSeriesData(
            [
                "testname_min",
                "testname_max",
                "testname_sum",
                "testname_count",
                "testname_last_value",
            ],
            [5, 5, 5, 1, 5],
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_value_observer(
            value_observer_record
        )
        self.assertEqual(timeseries, expected_timeseries)

    # Ensures conversion to timeseries function as expected for different aggregation types
    def test_convert_to_timeseries(self):
        empty_timeseries = TimeSeriesData([], [])
        timeseries_mock_method = mock.Mock(return_value=empty_timeseries)
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        exporter.convert_from_sum = timeseries_mock_method
        exporter.convert_from_min_max_sum_count = timeseries_mock_method
        exporter.convert_from_histogram = timeseries_mock_method
        exporter.convert_from_last_value = timeseries_mock_method
        exporter.convert_from_value_observer = timeseries_mock_method
        test_records = [
            MetricRecord(
                self._test_metric,
                self._labels_key,
                SumAggregator(),
                get_meter_provider().resource,
            ),
            MetricRecord(
                self._test_metric,
                self._labels_key,
                MinMaxSumCountAggregator(),
                get_meter_provider().resource,
            ),
            MetricRecord(
                self._test_metric,
                self._labels_key,
                HistogramAggregator(),
                get_meter_provider().resource,
            ),
            MetricRecord(
                self._test_metric,
                self._labels_key,
                LastValueAggregator(),
                get_meter_provider().resource,
            ),
            MetricRecord(
                self._test_metric,
                self._labels_key,
                ValueObserverAggregator(),
                get_meter_provider().resource,
            ),
        ]
        data = exporter.convert_to_timeseries(test_records)
        self.assertEqual(len(data), 5)
        for timeseries in data:
            self.assertEqual(timeseries, empty_timeseries)

        no_type_records = [
            MetricRecord(
                self._test_metric,
                self._labels_key,
                None,
                get_meter_provider().resource,
            )
        ]
        with self.assertRaises(ValueError):
            exporter.convert_to_timeseries(no_type_records)
        no_label_records = [
            MetricRecord(
                self._test_metric,
                self._labels_key,
                None,
                get_meter_provider().resource,
            )
        ]
        with self.assertRaises(ValueError):
            exporter.convert_to_timeseries(no_label_records)

    # Verifies that build_message calls snappy.compress and returns SerializedString
    @mock.patch("snappy.compress", return_value=1)
    def test_build_message(self, mock_compress):
        data = [
            TimeSeriesData(["test_label0"], [0]),
            TimeSeriesData(["test_label1"], [1]),
        ]
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        message = exporter.build_message(data)
        self.assertEqual(mock_compress.call_count, 1)
        self.assertIsInstance(message, str)

    # Ensure correct headers are added when valid config is provided
    def test_get_headers(self):
        test_config = self._test_config
        test_config["headers"] = {"Custom Header": "test_header"}
        test_config["bearer_token"] = "test_token"
        exporter = PrometheusRemoteWriteMetricsExporter(test_config)
        headers = exporter.get_headers()
        self.assertEqual(headers["Content-Encoding"], "snappy")
        self.assertEqual(headers["Content-Type"], "application/x-protobuf")
        self.assertEqual(headers["X-Prometheus-Remote-Write-Version"], "0.1.0")
        self.assertEqual(headers["Authorization"], "test_token")
        self.assertEqual(headers["Custom Header"], "test_header")

    def test_send_request(self):
        # TODO: Iron out details of test after implementation
        pass

    # Ensures non alphanumberic label characters gets replaced with underscore
    def test_sanitize_label(self):
        unsanitized_string = "key/metric@data"
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        sanitized_string = exporter.sanitize_label(unsanitized_string)
        self.assertEqual(sanitized_string, "key_metric_data")
