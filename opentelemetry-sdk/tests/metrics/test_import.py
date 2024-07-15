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

# pylint: disable=unused-import,import-outside-toplevel,too-many-locals

from opentelemetry.test import TestCase


class TestImport(TestCase):
    def test_import_init(self):
        """
        Test that the metrics root module has the right symbols
        """

        with self.assertNotRaises(Exception):
            from opentelemetry.sdk.metrics import (  # noqa: F401
                Counter,
                Histogram,
                Meter,
                MeterProvider,
                ObservableCounter,
                ObservableGauge,
                ObservableUpDownCounter,
                UpDownCounter,
                _Gauge,
            )

    def test_import_export(self):
        """
        Test that the metrics export module has the right symbols
        """

        with self.assertNotRaises(Exception):
            from opentelemetry.sdk.metrics.export import (  # noqa: F401
                AggregationTemporality,
                ConsoleMetricExporter,
                DataPointT,
                DataT,
                Gauge,
                Histogram,
                HistogramDataPoint,
                InMemoryMetricReader,
                Metric,
                MetricExporter,
                MetricExportResult,
                MetricReader,
                MetricsData,
                NumberDataPoint,
                PeriodicExportingMetricReader,
                ResourceMetrics,
                ScopeMetrics,
                Sum,
            )

    def test_import_view(self):
        """
        Test that the metrics view module has the right symbols
        """

        with self.assertNotRaises(Exception):
            from opentelemetry.sdk.metrics.view import (  # noqa: F401
                Aggregation,
                DefaultAggregation,
                DropAggregation,
                ExplicitBucketHistogramAggregation,
                LastValueAggregation,
                SumAggregation,
                View,
            )
