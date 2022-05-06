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


class TestImport(TestCase):
    def test_import_init(self):
        """
        Test that the metrics root module has the right symbols
        """

        try:
            from opentelemetry.sdk._metrics import (
                Aggregation,
                AggregationTemporality,
                Counter,
                DefaultAggregation,
                DropAggregation,
                ExplicitBucketHistogramAggregation,
                Histogram,
                LastValueAggregation,
                Meter,
                MeterProvider,
                ObservableCounter,
                ObservableGauge,
                ObservableUpDownCounter,
                SumAggregation,
                UpDownCounter,
            )

            Meter
            MeterProvider
            Aggregation
            AggregationTemporality
            DefaultAggregation
            DropAggregation
            ExplicitBucketHistogramAggregation
            LastValueAggregation
            SumAggregation
            Counter
            Histogram
            ObservableCounter
            ObservableGauge
            ObservableUpDownCounter
            UpDownCounter

        except Exception as error:
            self.fail(f"Unexpected error {error} was raised")

    def test_import_export(self):
        """
        Test that the metrics export module has the right symbols
        """

        try:
            from opentelemetry.sdk._metrics.export import (
                ConsoleMetricExporter,
                Gauge,
                Histogram,
                InMemoryMetricReader,
                Metric,
                MetricExporter,
                MetricExportResult,
                MetricReader,
                PeriodicExportingMetricReader,
                PointT,
                Sum,
            )

            ConsoleMetricExporter
            InMemoryMetricReader
            MetricExporter
            MetricExportResult
            MetricReader
            PeriodicExportingMetricReader
            Gauge
            Histogram
            Metric
            PointT
            Sum
        except Exception as error:
            self.fail(f"Unexpected error {error} was raised")
