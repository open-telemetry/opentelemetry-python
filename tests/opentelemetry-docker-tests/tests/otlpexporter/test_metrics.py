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

from __future__ import annotations

import unittest

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from . import METRIC_EXPORTERS


def _setup(factory):
    reader = PeriodicExportingMetricReader(factory())
    provider = MeterProvider(metric_readers=[reader])
    meter = provider.get_meter(
        "test.meter", version="0.1.0", schema_url="https://example.com"
    )
    return provider, meter


class TestMetricExport(unittest.TestCase):
    def test_counter(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                counter = meter.create_counter(
                    "test_counter", unit="requests", description="A counter"
                )
                counter.add(1, {"endpoint": "/api"})
                counter.add(5, {"endpoint": "/health"})

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_up_down_counter(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                udc = meter.create_up_down_counter(
                    "active_connections",
                    unit="connections",
                    description="Gauge-like counter",
                )
                udc.add(3, {"pool": "main"})
                udc.add(-1, {"pool": "main"})

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_histogram(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                histogram = meter.create_histogram(
                    "request_duration",
                    unit="ms",
                    description="Duration histogram",
                )
                for val in (5, 12, 50, 120, 350):
                    histogram.record(val, {"method": "GET"})

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_gauge(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                gauge = meter.create_gauge(
                    "cpu_usage", unit="%", description="CPU gauge"
                )
                gauge.set(65.3, {"host": "node-1"})
                gauge.set(42.1, {"host": "node-2"})

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_observable_counter(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                meter.create_observable_counter(
                    "bytes_read",
                    callbacks=[
                        lambda _: [Observation(1024, {"device": "eth0"})]
                    ],
                    unit="By",
                    description="Observable counter",
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_observable_up_down_counter(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                meter.create_observable_up_down_counter(
                    "thread_count",
                    callbacks=[lambda _: [Observation(8, {"pool": "io"})]],
                    unit="threads",
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_observable_gauge(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                meter.create_observable_gauge(
                    "temperature",
                    callbacks=[
                        lambda _: [Observation(72.5, {"location": "room-1"})]
                    ],
                    unit="F",
                    description="Observable gauge",
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_multiple_attributes(self):
        """Multiple attribute sets on the same instrument produce distinct series."""
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, meter = _setup(factory)

                counter = meter.create_counter("multi_attr_counter")
                counter.add(1, {"region": "us-east", "env": "prod"})
                counter.add(2, {"region": "eu-west", "env": "staging"})
                counter.add(3, {"region": "us-east", "env": "prod"})

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_resource_attributes(self):
        for protocol, factory in METRIC_EXPORTERS:
            with self.subTest(protocol=protocol):
                resource = Resource.create(
                    {"service.name": "test-svc", "service.version": "1.0.0"}
                )
                reader = PeriodicExportingMetricReader(factory())
                provider = MeterProvider(
                    metric_readers=[reader], resource=resource
                )
                meter = provider.get_meter("test.meter")

                counter = meter.create_counter("resource_counter")
                counter.add(1)

                self.assertTrue(provider.force_flush())
                provider.shutdown()
