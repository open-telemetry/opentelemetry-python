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

import time
from threading import Lock

from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    MetricsData,
    PeriodicExportingMetricReader,
)
from opentelemetry.test.concurrency_test import ConcurrencyTestBase


class MaxCountExporter(MetricExporter):
    def __init__(self) -> None:
        super().__init__(None, None)
        self._lock = Lock()

        # the number of threads inside of export()
        self.count_in_export = 0

        # the total count of calls to export()
        self.export_count = 0

        # the maximum number of threads in export() ever
        self.max_count_in_export = 0

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        with self._lock:
            self.export_count += 1
            self.count_in_export += 1

        # yield to other threads
        time.sleep(0)

        with self._lock:
            self.max_count_in_export = max(
                self.max_count_in_export, self.count_in_export
            )
            self.count_in_export -= 1

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass


class TestExporterConcurrency(ConcurrencyTestBase):
    """
    Tests the requirement that:

    > `Export` will never be called concurrently for the same exporter instance.  `Export` can
    > be called again only after the current call returns.

    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exportbatch

    This test also tests that a thread that calls the a
    ``MetricReader.collect`` method using an asynchronous instrument is able
    to perform two actions in the same thread lock space (without it being
    interrupted by another thread):

    1. Consume the measurement produced by the callback associated to the
       asynchronous instrument.
    2. Export the measurement mentioned in the step above.
    """

    def test_exporter_not_called_concurrently(self):
        exporter = MaxCountExporter()
        reader = PeriodicExportingMetricReader(
            exporter=exporter,
            export_interval_millis=100_000,
        )
        meter_provider = MeterProvider(metric_readers=[reader])

        counter_cb_counter = 0

        def counter_cb(options: CallbackOptions):
            nonlocal counter_cb_counter
            counter_cb_counter += 1
            yield Observation(2)

        meter_provider.get_meter(__name__).create_observable_counter(
            "testcounter", callbacks=[counter_cb]
        )

        # call collect from a bunch of threads to try and enter export() concurrently
        def test_many_threads():
            reader.collect()

        self.run_with_many_threads(test_many_threads, num_threads=100)

        self.assertEqual(counter_cb_counter, 100)
        # no thread should be in export() now
        self.assertEqual(exporter.count_in_export, 0)
        # should be one call for each thread
        self.assertEqual(exporter.export_count, 100)
        # should never have been more than one concurrent call
        self.assertEqual(exporter.max_count_in_export, 1)
