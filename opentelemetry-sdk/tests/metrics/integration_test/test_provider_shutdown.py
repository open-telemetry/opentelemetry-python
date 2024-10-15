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

import gc
import time
import weakref
from typing import Sequence
from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    Metric,
    MetricExporter,
    MetricExportResult,
    PeriodicExportingMetricReader,
)


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
        time.sleep(self.wait)
        self.metrics.extend(metrics_data)
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._shutdown = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class TestMeterProviderShutdown(TestCase):
    def test_meter_provider_shutdown_cleans_up_successfully(self):
        def create_and_shutdown():
            exporter = FakeMetricsExporter()
            exporter_wr = weakref.ref(exporter)

            reader = PeriodicExportingMetricReader(exporter)
            reader_wr = weakref.ref(reader)

            provider = MeterProvider(metric_readers=[reader])
            provider_wr = weakref.ref(provider)

            provider.shutdown()

            return exporter_wr, reader_wr, provider_wr

        # When: the provider is shutdown
        (
            exporter_weakref,
            reader_weakref,
            provider_weakref,
        ) = create_and_shutdown()
        gc.collect()

        # Then: the provider, exporter and reader should be garbage collected
        self.assertIsNone(exporter_weakref())
        self.assertIsNone(reader_weakref())
        self.assertIsNone(provider_weakref())
