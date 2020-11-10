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

import os
import unittest
from unittest import mock

import yaml

from opentelemetry.exporter.prometheus_remote_write import (
    Config,
    PrometheusRemoteWriteMetricsExporter,
    TimeSeriesData,
    parse_config,
    sanitize_label,
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
            [
                "testname_min",
                "testname_max",
                "testname_sum",
                "testname_count"
            ], [5, 5, 5, 1]
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_min_max_sum_count(min_max_sum_count_record)
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
                "testname_{le=\"0\"}",
                "testname_{le=\"+Inf\"}"
            ], [1, 5, 0, 1]
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
            ], [5, 5, 5, 1, 5]
        )
        exporter = PrometheusRemoteWriteMetricsExporter(self._test_config)
        timeseries = exporter.convert_from_value_observer(value_observer_record)
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
            ), MetricRecord(
                self._test_metric,
                self._labels_key,
                MinMaxSumCountAggregator(),
                get_meter_provider().resource,
            ), MetricRecord(
                self._test_metric,
                self._labels_key,
                HistogramAggregator(),
                get_meter_provider().resource,
            ), MetricRecord(
                self._test_metric,
                self._labels_key,
                LastValueAggregator(),
                get_meter_provider().resource,
            ), MetricRecord(
                self._test_metric,
                self._labels_key,
                ValueObserverAggregator(),
                get_meter_provider().resource,
            )
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
    @mock.patch('snappy.compress', return_value=1)
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
        test_config["headers"] = {
            "Custom Header": "test_header"
        }
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

    def test_build_client(self):
        # TODO: Iron out details of test after implementation
        pass

    # Ensures non alphanumberic label characters gets replaced with underscore
    def test_sanitize_label(self):
        unsanitized_string = "key/metric@data"
        sanitized_string = sanitize_label(unsanitized_string)
        self.assertEqual(sanitized_string, "key_metric_data")

    # Verifies that valid yaml file is parsed correctly
    def test_valid_yaml_file(self):
        yml_dict = [
            {"url": ["https://testurl.com"]},
            {"name": ["test_name"]},
            {"remote_timeout": ["30s"]},
        ]
        filepath = "./test.yml"
        with open(filepath, 'w') as file:
            yaml.dump(yml_dict, file)
        config = parse_config(filepath)
        os.remove(filepath)
        self.assertEqual(config["url"], "https://testurl.com")
        self.assertEqual(config["name"], "test_name")
        self.assertEqual(config["remote_timeout"], "30s")

    # Ensures invalid filepath raises error when parsing
    def test_invalid_yaml_file(self):
        filepath = "invalid filepath"
        with self.assertRaises(ValueError):
            parse_config(filepath)

    # Series of test cases to ensure config validation works as intended
    class TestConfig(unittest.TestCase):
        def test_valid_standard_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_valid_basic_auth_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "basic_auth": {
                    "username": "test_username",
                    "password": "test_password",
                }
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_valid_bearer_token_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "bearer_token": "test_token",
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_valid_quantiles_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "quantiles": [0.25, 0.5, 0.75],
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_valid_histogram_boundaries_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "histogram_boundaries": [0, 5, 10],
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_valid_tls_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "tls_config": {
                    "ca_file": "test_ca_file",
                    "cert_file": "test_cert_file",
                    "key_file": "test_key_file",
                }
            })
            try:
                config.validate()
            except ValueError:
                self.fail("valid config failed config.validate()")

        def test_invalid_no_url_config(self):
            config = Config({
                "name": "test_name",
                "remote_timeout": "30s",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_no_name_config(self):
            config = Config({
                "url": "https://testurl.com",
                "remote_timeout": "30s",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_no_remote_timeout_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_no_username_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "basic_auth": {
                    "password": "test_password",
                }
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_no_password_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "basic_auth": {
                    "username": "test_username",
                }
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_conflicting_passwords_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "basic_auth": {
                    "username": "test_username",
                    "password": "test_password",
                    "password_file": "test_password_file",
                }
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_conflicting_bearer_tokens_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "bearer_token": "test_token",
                "bearer_token_file": "test_token_file",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_conflicting_auth_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "basic_auth": {
                    "username": "test_username",
                    "password": "test_password",
                },
                "bearer_token": "test_token",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_quantiles_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "quantiles": "0.25, 0.5, 0.75",
            })
            with self.assertRaises(ValueError):
                config.validate()

        def test_invalid_histogram_boundaries_config(self):
            config = Config({
                "url": "https://testurl.com",
                "name": "test_name",
                "remote_timeout": "30s",
                "histogram_boundaries": "0, 5, 10",
            })
            with self.assertRaises(ValueError):
                config.validate()
