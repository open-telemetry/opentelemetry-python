# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=unused-import,import-outside-toplevel,too-many-locals

from opentelemetry.test import TestCase


class TestImport(TestCase):
    def test_import_init(self):
        """
        Test that the metrics root module has the right symbols
        """

        with self.assertNotRaises(Exception):
            from opentelemetry.sdk.metrics import (  # noqa: F401, PLC0415
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
            from opentelemetry.sdk.metrics.export import (  # noqa: F401, PLC0415
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
            from opentelemetry.sdk.metrics.view import (  # noqa: F401, PLC0415
                Aggregation,
                DefaultAggregation,
                DropAggregation,
                ExplicitBucketHistogramAggregation,
                LastValueAggregation,
                SumAggregation,
                View,
            )
