# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import WARNING
from unittest import TestCase

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import View


class TestAttributesAdvisory(TestCase):
    _SYNC_INSTRUMENTS = {
        "counter": ("create_counter", "add"),
        "up_down_counter": ("create_up_down_counter", "add"),
        "histogram": ("create_histogram", "record"),
        "gauge": ("create_gauge", "set"),
    }

    _ASYNC_INSTRUMENTS = {
        "observable_counter": "create_observable_counter",
        "observable_up_down_counter": "create_observable_up_down_counter",
        "observable_gauge": "create_observable_gauge",
    }

    _ALL_INSTRUMENTS = (*_SYNC_INSTRUMENTS, *_ASYNC_INSTRUMENTS)

    def _collect_attributes(self, reader):
        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        return [dict(data_point.attributes) for data_point in metric.data.data_points]

    def _record(self, meter, instrument, attributes, attributes_advisory=None):
        if instrument in self._SYNC_INSTRUMENTS:
            create_method, record_method = self._SYNC_INSTRUMENTS[instrument]
            synchronous = getattr(meter, create_method)("testinstrument", _attributes_advisory=attributes_advisory)
            getattr(synchronous, record_method)(1, attributes)
        else:
            create_method = self._ASYNC_INSTRUMENTS[instrument]
            getattr(meter, create_method)(
                "testinstrument",
                callbacks=[lambda options, values=attributes: [Observation(1, values)]],
                _attributes_advisory=attributes_advisory,
            )

    def test_advisory(self):
        for instrument in self._ALL_INSTRUMENTS:
            with self.subTest(instrument=instrument):
                reader = InMemoryMetricReader()
                meter = MeterProvider(metric_readers=[reader]).get_meter("m")
                self._record(
                    meter,
                    instrument,
                    {"label": "value", "dropped": "value"},
                    attributes_advisory=["label"],
                )

                self.assertEqual(self._collect_attributes(reader), [{"label": "value"}])

    def test_histogram_combines_advisories(self):
        reader = InMemoryMetricReader()
        meter = MeterProvider(metric_readers=[reader]).get_meter("m")
        histogram = meter.create_histogram(
            "testinstrument",
            explicit_bucket_boundaries_advisory=[1.0, 2.0],
            _attributes_advisory=["label"],
        )
        histogram.record(1, {"label": "value", "dropped": "value"})

        metrics = reader.get_metrics_data()
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        data_point = metric.data.data_points[0]
        self.assertEqual(dict(data_point.attributes), {"label": "value"})
        self.assertEqual(data_point.explicit_bounds, (1.0, 2.0))

    def test_no_advisory(self):
        for instrument in self._ALL_INSTRUMENTS:
            with self.subTest(instrument=instrument):
                reader = InMemoryMetricReader()
                meter = MeterProvider(metric_readers=[reader]).get_meter("m")
                self._record(
                    meter,
                    instrument,
                    {"label": "value", "kept": "value"},
                )

                self.assertEqual(
                    self._collect_attributes(reader),
                    [{"label": "value", "kept": "value"}],
                )

    def test_empty_advisory(self):
        for instrument in self._ALL_INSTRUMENTS:
            with self.subTest(instrument=instrument):
                reader = InMemoryMetricReader()
                meter = MeterProvider(metric_readers=[reader]).get_meter("m")
                self._record(
                    meter,
                    instrument,
                    {"label": "value"},
                    attributes_advisory=[],
                )

                self.assertEqual(self._collect_attributes(reader), [{}])

    def test_view_without_attribute_keys(self):
        for instrument in self._ALL_INSTRUMENTS:
            with self.subTest(instrument=instrument):
                reader = InMemoryMetricReader()
                meter = MeterProvider(
                    metric_readers=[reader],
                    views=[View(instrument_name="testinstrument", name="renamed")],
                ).get_meter("m")
                self._record(
                    meter,
                    instrument,
                    {"label": "value", "dropped": "value"},
                    attributes_advisory=["label"],
                )

                self.assertEqual(self._collect_attributes(reader), [{"label": "value"}])

    def test_view_overrides_advisory(self):
        for instrument in self._ALL_INSTRUMENTS:
            with self.subTest(instrument=instrument):
                reader = InMemoryMetricReader()
                meter = MeterProvider(
                    metric_readers=[reader],
                    views=[
                        View(
                            instrument_name="testinstrument",
                            attribute_keys={"other"},
                        )
                    ],
                ).get_meter("m")
                self._record(
                    meter,
                    instrument,
                    {"label": "value", "other": "value"},
                    attributes_advisory=["label"],
                )

                self.assertEqual(self._collect_attributes(reader), [{"other": "value"}])

    def test_invalid_advisory_ignored(self):
        for instrument in self._ALL_INSTRUMENTS:
            for invalid_advisory in (
                ["label", 1],
                [None],
                "label",
                123,
            ):
                with self.subTest(instrument=instrument, invalid_advisory=invalid_advisory):
                    reader = InMemoryMetricReader()
                    meter = MeterProvider(metric_readers=[reader]).get_meter("m")

                    # the warning is emitted when the instrument is created
                    with self.assertLogs(level=WARNING) as log:
                        self._record(
                            meter,
                            instrument,
                            {"label": "value", "kept": "value"},
                            attributes_advisory=invalid_advisory,
                        )
                    self.assertIn(
                        "_attributes_advisory must be a sequence of strings",
                        log.records[0].message,
                    )

                    self.assertEqual(
                        self._collect_attributes(reader),
                        [{"label": "value", "kept": "value"}],
                    )
