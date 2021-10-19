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


from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics import (
    MeterProvider,
    MetricExporter,
    MetricReader,
    View,
)
from opentelemetry.sdk.resources import Resource


class TestMeterProvider(TestCase):
    def test_meter_provider_resource(self):
        """
        `MeterProvider` provides a way to allow a `Resource` to be specified.
        """

        meter_provider_0 = MeterProvider()
        meter_provider_1 = MeterProvider()

        self.assertIs(meter_provider_0.resource, meter_provider_1.resource)
        self.assertIsInstance(meter_provider_0.resource, Resource)
        self.assertIsInstance(meter_provider_1.resource, Resource)

        resource = Resource({"key": "value"})
        self.assertIs(MeterProvider(resource).resource, resource)

    def test_get_meter(self):
        """
        `MeterProvider.get_meter` arguments are used to create an
        `InstrumentationInfo` object on the created `Meter`.
        """

        meter = MeterProvider().get_meter(
            "name",
            version="version",
            schema_url="schema_url",
        )

        self.assertEqual(meter._instrumentation_info.name, "name")
        self.assertEqual(meter._instrumentation_info.version, "version")
        self.assertEqual(meter._instrumentation_info.schema_url, "schema_url")

    def test_register_metric_reader(self):
        """ "
        `MeterProvider` provides a way to configure `MetricReader`s.
        """

        meter_provider = MeterProvider()

        self.assertTrue(hasattr(meter_provider, "register_metric_reader"))

        metric_reader = MetricReader()

        meter_provider.register_metric_reader(metric_reader)

        self.assertTrue(meter_provider._metric_readers, [metric_reader])

    def test_register_metric_exporter(self):
        """ "
        `MeterProvider` provides a way to configure `MetricExporter`s.
        """

        meter_provider = MeterProvider()

        self.assertTrue(hasattr(meter_provider, "register_metric_exporter"))

        metric_exporter = MetricExporter()

        meter_provider.register_metric_exporter(metric_exporter)

        self.assertTrue(meter_provider._metric_exporters, [metric_exporter])

    def test_register_view(self):
        """ "
        `MeterProvider` provides a way to configure `View`s.
        """

        meter_provider = MeterProvider()

        self.assertTrue(hasattr(meter_provider, "register_view"))

        view = View()

        meter_provider.register_view(view)

        self.assertTrue(meter_provider._views, [view])

    def test_meter_configuration(self):
        """
        Any updated configuration is applied to all returned `Meter`s.
        """

        meter_provider = MeterProvider()

        view_0 = View()

        meter_provider.register_view(view_0)

        meter_0 = meter_provider.get_meter("meter_0")
        meter_1 = meter_provider.get_meter("meter_1")

        self.assertEqual(meter_0._meter_provider.views, [view_0])
        self.assertEqual(meter_1._meter_provider.views, [view_0])

        view_1 = View()

        meter_provider.register_view(view_1)

        self.assertEqual(meter_0._meter_provider.views, [view_0, view_1])
        self.assertEqual(meter_1._meter_provider.views, [view_0, view_1])

    def test_shutdown_subsequent_calls(self):
        """
        No subsequent attempts to get a `Meter` are allowed after calling
        `MeterProvider.shutdown`
        """

        meter_provider = MeterProvider()

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                meter_provider.shutdown()

        with self.assertLogs(level=WARNING):
            meter_provider.shutdown()

    def test_shutdown_result(self):
        """
        `MeterProvider.shutdown` provides a way to let the caller know if it
        succeeded or failed.

        `MeterProvider.shutdown` is implemented by at least invoking
        ``shutdown`` on all registered `MetricReader`s and `MetricExporter`s.
        """

        meter_provider = MeterProvider()

        meter_provider.register_metric_reader(
            Mock(**{"shutdown.return_value": True})
        )
        meter_provider.register_metric_exporter(
            Mock(**{"shutdown.return_value": True})
        )

        self.assertTrue(meter_provider.shutdown())

        meter_provider = MeterProvider()

        meter_provider.register_metric_reader(
            Mock(**{"shutdown.return_value": True})
        )
        meter_provider.register_metric_exporter(
            Mock(**{"shutdown.return_value": False})
        )

        self.assertFalse(meter_provider.shutdown())

    def test_force_flush_result(self):
        """
        `MeterProvider.force_flush` provides a way to let the caller know if it
        succeeded or failed.

        `MeterProvider.force_flush` is implemented by at least invoking
        ``force_flush`` on all registered `MetricReader`s and `MetricExporter`s.
        """

        meter_provider = MeterProvider()

        meter_provider.register_metric_reader(
            Mock(**{"force_flush.return_value": True})
        )
        meter_provider.register_metric_exporter(
            Mock(**{"force_flush.return_value": True})
        )

        self.assertTrue(meter_provider.force_flush())

        meter_provider = MeterProvider()

        meter_provider.register_metric_reader(
            Mock(**{"force_flush.return_value": True})
        )
        meter_provider.register_metric_exporter(
            Mock(**{"force_flush.return_value": False})
        )

        self.assertFalse(meter_provider.force_flush())
