# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import View


class TestInstrumentNameCase(TestCase):
    _INSTRUMENTS = (
        ("counter", "add"),
        ("up_down_counter", "add"),
        ("histogram", "record"),
        ("gauge", "set"),
        ("observable_counter", None),
        ("observable_up_down_counter", None),
        ("observable_gauge", None),
    )

    def _setup_meter(self, views=()):
        reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[reader], views=views)
        self.addCleanup(provider.shutdown)
        return provider.get_meter("testmeter"), reader

    @staticmethod
    def _create_instrument(meter, kind, name):
        factory = getattr(meter, f"create_{kind}")
        if kind.startswith("observable_"):
            return factory(name, callbacks=[lambda options: [Observation(7)]])
        return factory(name)

    def test_collected_metric_names_preserve_case(self):
        for kind, record in self._INSTRUMENTS:
            with self.subTest(kind=kind):
                meter, reader = self._setup_meter()
                instrument = self._create_instrument(meter, kind, "RequestCount")
                if record is not None:
                    getattr(instrument, record)(7)
                metrics = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics
                self.assertEqual(len(metrics), 1)
                self.assertEqual(metrics[0].name, "RequestCount")

    def test_repeated_name_keeps_first_case(self):
        for kind, record in self._INSTRUMENTS:
            with self.subTest(kind=kind):
                meter, reader = self._setup_meter()
                first = self._create_instrument(meter, kind, "RequestCount")
                with self.assertNoLogs("opentelemetry.sdk.metrics._internal", level="WARNING"):
                    self.assertIs(self._create_instrument(meter, kind, "RequestCount"), first)
                with self.assertLogs("opentelemetry.sdk.metrics._internal", level="WARNING") as logs:
                    duplicate = self._create_instrument(meter, kind, "requestcount")
                self.assertIs(duplicate, first)
                if record is not None:
                    getattr(duplicate, record)(7)
                metric = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0]
                self.assertEqual(metric.name, "RequestCount")
                self.assertIn("RequestCount", logs.output[0])
                self.assertIn("requestcount", logs.output[0])

    def test_view_matches_instrument_name_case_insensitively(self):
        for kind, record in (("counter", "add"), ("observable_gauge", None)):
            for pattern in ("requestcount", "REQUESTCOUNT", "request*", "REQUEST*"):
                with self.subTest(kind=kind, pattern=pattern):
                    meter, reader = self._setup_meter(views=[View(instrument_name=pattern, description="matched")])
                    instrument = self._create_instrument(meter, kind, "RequestCount")
                    if record is not None:
                        getattr(instrument, record)(7)
                    metric = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0]
                    self.assertEqual(metric.description, "matched")
                    self.assertEqual(metric.name, "RequestCount")

    def test_view_rename_preserves_configured_case(self):
        meter, reader = self._setup_meter(views=[View(instrument_name="requestcount", name="ExportedCount")])
        meter.create_counter("RequestCount").add(7)
        metric = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "ExportedCount")

    def test_conflict_warning_remains_case_insensitive(self):
        meter, _ = self._setup_meter(views=[View(instrument_name="*")])
        meter.create_counter("RequestCount", description="first").add(1)
        with self.assertLogs("opentelemetry.sdk.metrics._internal.metric_reader_storage", level="WARNING"):
            meter.create_counter("requestcount", description="second").add(1)
