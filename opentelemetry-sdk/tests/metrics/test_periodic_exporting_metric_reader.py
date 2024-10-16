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

# pylint: disable=protected-access,invalid-name,no-self-use

import math
from logging import WARNING
from time import sleep, time_ns
from typing import Optional, Sequence
from unittest.mock import Mock

from flaky import flaky

from opentelemetry.sdk.metrics import Counter, MetricsTimeoutError
from opentelemetry.sdk.metrics._internal import _Counter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    MetricExporter,
    MetricExportResult,
    NumberDataPoint,
    PeriodicExportingMetricReader,
    Sum,
)
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    LastValueAggregation,
)
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class FakeMetricsExporter(MetricExporter):
    def __init__(
        self, wait=0, preferred_temporality=None, preferred_aggregation=None
    ):
        self.wait = wait
        self.metrics = []
        self._shutdown = False
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def export(
        self,
        metrics_data: Sequence[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        sleep(self.wait)
        self.metrics.extend(metrics_data)
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._shutdown = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class ExceptionAtCollectionPeriodicExportingMetricReader(
    PeriodicExportingMetricReader
):
    def __init__(
        self,
        exporter: MetricExporter,
        exception: Exception,
        export_interval_millis: Optional[float] = None,
        export_timeout_millis: Optional[float] = None,
    ) -> None:
        super().__init__(
            exporter, export_interval_millis, export_timeout_millis
        )
        self._collect_exception = exception

    # pylint: disable=overridden-final-method
    def collect(self, timeout_millis: float = 10_000) -> None:
        raise self._collect_exception


metrics_list = [
    Metric(
        name="sum_name",
        description="",
        unit="",
        data=Sum(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ],
            aggregation_temporality=1,
            is_monotonic=True,
        ),
    ),
    Metric(
        name="gauge_name",
        description="",
        unit="",
        data=Gauge(
            data_points=[
                NumberDataPoint(
                    attributes={},
                    start_time_unix_nano=time_ns(),
                    time_unix_nano=time_ns(),
                    value=2,
                )
            ]
        ),
    ),
]


class TestPeriodicExportingMetricReader(ConcurrencyTestBase):
    def test_defaults(self):
        pmr = PeriodicExportingMetricReader(FakeMetricsExporter())
        self.assertEqual(pmr._export_interval_millis, 60000)
        self.assertEqual(pmr._export_timeout_millis, 30000)
        with self.assertLogs(level=WARNING):
            pmr.shutdown()

    def _create_periodic_reader(
        self, metrics, exporter, collect_wait=0, interval=60000, timeout=30000
    ):
        pmr = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=interval,
            export_timeout_millis=timeout,
        )

        def _collect(reader, timeout_millis):
            sleep(collect_wait)
            pmr._receive_metrics(metrics, timeout_millis)

        pmr._set_collect_callback(_collect)
        return pmr

    def test_ticker_called(self):
        collect_mock = Mock()
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        pmr = PeriodicExportingMetricReader(exporter, export_interval_millis=1)
        pmr._set_collect_callback(collect_mock)
        sleep(0.1)
        self.assertTrue(collect_mock.assert_called_once)
        pmr.shutdown()

    def test_ticker_not_called_on_infinity(self):
        collect_mock = Mock()
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        pmr = PeriodicExportingMetricReader(
            exporter, export_interval_millis=math.inf
        )
        pmr._set_collect_callback(collect_mock)
        sleep(0.1)
        self.assertTrue(collect_mock.assert_not_called)
        pmr.shutdown()

    def test_ticker_value_exception_on_zero(self):
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        self.assertRaises(
            ValueError,
            PeriodicExportingMetricReader,
            exporter,
            export_interval_millis=0,
        )

    def test_ticker_value_exception_on_negative(self):
        exporter = FakeMetricsExporter()
        exporter.export = Mock()
        self.assertRaises(
            ValueError,
            PeriodicExportingMetricReader,
            exporter,
            export_interval_millis=-100,
        )

    @flaky(max_runs=3, min_passes=1)
    def test_ticker_collects_metrics(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader(
            metrics_list, exporter, interval=100
        )
        sleep(0.15)
        self.assertEqual(exporter.metrics, metrics_list)
        pmr.shutdown()

    def test_shutdown(self):
        exporter = FakeMetricsExporter()

        pmr = self._create_periodic_reader([], exporter)
        pmr.shutdown()
        self.assertEqual(exporter.metrics, [])
        self.assertTrue(pmr._shutdown)
        self.assertTrue(exporter._shutdown)

    def test_shutdown_multiple_times(self):
        pmr = self._create_periodic_reader([], FakeMetricsExporter())
        with self.assertLogs(level="WARNING") as w:
            self.run_with_many_threads(pmr.shutdown)
        self.assertTrue("Can't shutdown multiple times" in w.output[0])
        with self.assertLogs(level="WARNING") as w:
            pmr.shutdown()

    def test_exporter_temporality_preference(self):
        exporter = FakeMetricsExporter(
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
            },
        )
        pmr = PeriodicExportingMetricReader(exporter)
        for key, value in pmr._instrument_class_temporality.items():
            if key is not _Counter:
                self.assertEqual(value, AggregationTemporality.CUMULATIVE)
            else:
                self.assertEqual(value, AggregationTemporality.DELTA)

    def test_exporter_aggregation_preference(self):
        exporter = FakeMetricsExporter(
            preferred_aggregation={
                Counter: LastValueAggregation(),
            },
        )
        pmr = PeriodicExportingMetricReader(exporter)
        for key, value in pmr._instrument_class_aggregation.items():
            if key is not _Counter:
                self.assertTrue(isinstance(value, DefaultAggregation))
            else:
                self.assertTrue(isinstance(value, LastValueAggregation))

    def test_metric_timeout_does_not_kill_worker_thread(self):
        exporter = FakeMetricsExporter()
        pmr = ExceptionAtCollectionPeriodicExportingMetricReader(
            exporter,
            MetricsTimeoutError("test timeout"),
            export_timeout_millis=1,
        )

        sleep(0.1)
        self.assertTrue(pmr._daemon_thread.is_alive())
        pmr.shutdown()
