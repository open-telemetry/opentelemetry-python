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

"""
The purpose of this test is to test for backward compatibility with any user-implementable
interfaces as they were originally defined. For example, changes to the MetricExporter ABC must
be made in such a way that existing implementations (outside of this repo) continue to work
when *called* by the SDK.

This does not apply to classes which are not intended to be overriden by the user e.g.  Meter
and PeriodicExportingMetricReader concrete class. Those may freely be modified in a
backward-compatible way for *callers*.

Ideally, we could use mypy for this as well, but SDK is not type checked atm.
"""

from typing import Iterable, Sequence
from unittest import TestCase

from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    MetricExportResult,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.point import Metric


# Do not change these classes until after major version 1
class OrigMetricExporter(MetricExporter):
    def export(
        self,
        metrics: Sequence[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass


class OrigMetricReader(MetricReader):
    def _receive_metrics(
        self,
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self.collect()


class TestBackwardCompat(TestCase):
    def test_metric_exporter(self):
        exporter = OrigMetricExporter()
        meter_provider = MeterProvider(
            metric_readers=[PeriodicExportingMetricReader(exporter)]
        )
        # produce some data
        meter_provider.get_meter("foo").create_counter("mycounter").add(12)
        meter_provider.shutdown()

    def test_metric_reader(self):
        reader = OrigMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])
        # produce some data
        meter_provider.get_meter("foo").create_counter("mycounter").add(12)
        meter_provider.shutdown()
