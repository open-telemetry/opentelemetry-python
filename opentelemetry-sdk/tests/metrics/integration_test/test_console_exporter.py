# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from io import StringIO
from json import JSONDecoder, loads
from os import linesep
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.context import Context
from opentelemetry.metrics import get_meter, set_meter_provider
from opentelemetry.sdk.metrics import AlwaysOnExemplarFilter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.test.globals_test import reset_metrics_globals

TEST_TIMESTAMP = 1_234_567_890


class TestConsoleExporter(TestCase):
    def setUp(self):
        reset_metrics_globals()

    def tearDown(self):
        reset_metrics_globals()

    def test_console_exporter(self):
        output = StringIO()
        exporter = ConsoleMetricExporter(out=output)
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )
        provider = MeterProvider(metric_readers=[reader])
        set_meter_provider(provider)
        meter = get_meter(__name__)
        counter = meter.create_counter(
            "name", description="description", unit="unit"
        )
        counter.add(1, attributes={"a": "b"})
        provider.shutdown()

        output.seek(0)
        result_0 = loads("".join(output.readlines()))

        self.assertGreater(len(result_0), 0)

        metrics = result_0["resource_metrics"][0]["scope_metrics"][0]

        self.assertEqual(metrics["scope"]["name"], "test_console_exporter")

        metrics = metrics["metrics"][0]

        self.assertEqual(metrics["name"], "name")
        self.assertEqual(metrics["description"], "description")
        self.assertEqual(metrics["unit"], "unit")

        metrics = metrics["data"]

        self.assertEqual(metrics["aggregation_temporality"], 2)
        self.assertTrue(metrics["is_monotonic"])

        metrics = metrics["data_points"][0]

        self.assertEqual(metrics["attributes"], {"a": "b"})
        self.assertEqual(metrics["value"], 1)

    def test_console_exporter_no_export(self):
        output = StringIO()
        exporter = ConsoleMetricExporter(out=output)
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )
        provider = MeterProvider(metric_readers=[reader])
        provider.shutdown()

        output.seek(0)
        actual = "".join(output.readlines())
        expected = ""

        self.assertEqual(actual, expected)

    @patch(
        "opentelemetry.sdk.metrics._internal.instrument.time_ns",
        Mock(return_value=TEST_TIMESTAMP),
    )
    def test_console_exporter_with_exemplars(self):
        ctx = Context()

        output = StringIO()
        exporter = ConsoleMetricExporter(out=output)
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )
        provider = MeterProvider(
            metric_readers=[reader], exemplar_filter=AlwaysOnExemplarFilter()
        )
        set_meter_provider(provider)
        meter = get_meter(__name__)
        counter = meter.create_counter(
            "name", description="description", unit="unit"
        )
        counter.add(1, attributes={"a": "b"}, context=ctx)
        provider.shutdown()

        output.seek(0)
        joined_output = "".join(output.readlines())
        decoder = JSONDecoder()
        output_to_decode = joined_output.lstrip()
        results = []
        while output_to_decode:
            result, decoded_length = decoder.raw_decode(output_to_decode)
            results.append(result)
            output_to_decode = output_to_decode[decoded_length:].strip()
        result_0 = results[0]

        self.assertGreater(len(result_0), 0)

        metrics = result_0["resource_metrics"][0]["scope_metrics"][0]

        self.assertEqual(metrics["scope"]["name"], "test_console_exporter")

        point = metrics["metrics"][0]["data"]["data_points"][0]

        self.assertEqual(point["attributes"], {"a": "b"})
        self.assertEqual(point["value"], 1)
        self.assertEqual(
            point["exemplars"],
            [
                {
                    "filtered_attributes": {},
                    "value": 1,
                    "time_unix_nano": TEST_TIMESTAMP,
                    "span_id": None,
                    "trace_id": None,
                }
            ],
        )
