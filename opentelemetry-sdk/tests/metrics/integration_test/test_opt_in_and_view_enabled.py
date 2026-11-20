# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

from logging import WARNING
from unittest import TestCase

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import Gauge, InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
    View,
)


def _create_all_instruments(meter, *, opt_in_advisory=None):
    kwargs = {}
    if opt_in_advisory is not None:
        kwargs["_opt_in_advisory"] = opt_in_advisory

    counter = meter.create_counter("test_counter", **kwargs)
    up_down_counter = meter.create_up_down_counter("test_up_down_counter", **kwargs)
    histogram = meter.create_histogram("test_histogram", **kwargs)
    gauge = meter.create_gauge("test_gauge", **kwargs)
    observable_counter = meter.create_observable_counter(
        "test_observable_counter",
        callbacks=[lambda options: [Observation(1)]],
        **kwargs,
    )
    observable_up_down_counter = meter.create_observable_up_down_counter(
        "test_observable_up_down_counter",
        callbacks=[lambda options: [Observation(1)]],
        **kwargs,
    )
    observable_gauge = meter.create_observable_gauge(
        "test_observable_gauge",
        callbacks=[lambda options: [Observation(1)]],
        **kwargs,
    )

    counter.add(1)
    up_down_counter.add(1)
    histogram.record(1)
    gauge.set(1)

    return (
        counter,
        up_down_counter,
        histogram,
        gauge,
        observable_counter,
        observable_up_down_counter,
        observable_gauge,
    )


class TestOptInAdvisoryAndViewEnabled(TestCase):
    def test_opt_in_advisory_true_disabled_by_default(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])
        meter = meter_provider.get_meter("testmeter")

        _create_all_instruments(meter, opt_in_advisory=True)

        self.assertIsNone(reader.get_metrics_data())

    def test_opt_in_advisory_false_or_none_enabled_by_default(self):
        for opt_in_advisory in (None, False):
            with self.subTest(opt_in_advisory=opt_in_advisory):
                reader = InMemoryMetricReader()
                meter_provider = MeterProvider(metric_readers=[reader])
                meter = meter_provider.get_meter("testmeter")

                _create_all_instruments(meter, opt_in_advisory=opt_in_advisory)

                metrics_data = reader.get_metrics_data()
                self.assertIsNotNone(metrics_data)
                metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
                self.assertEqual(len(metrics), 7)

    def test_opt_in_advisory_true_matching_view_without_enabled_remains_disabled(
        self,
    ):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(
                    instrument_name="test_counter",
                    name="renamed_counter",
                    description="custom description",
                    attribute_keys={"k"},
                    aggregation=SumAggregation(),
                ),
                View(
                    instrument_name="test_histogram",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=[1.0, 5.0]),
                ),
                View(instrument_name="test_*"),
            ],
        )
        meter = meter_provider.get_meter("testmeter")

        _create_all_instruments(meter, opt_in_advisory=True)

        self.assertIsNone(reader.get_metrics_data())

    def test_opt_in_advisory_true_enabled_by_view(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[View(instrument_name="test_*", enabled=True)],
        )
        meter = meter_provider.get_meter("testmeter")

        _create_all_instruments(meter, opt_in_advisory=True)

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            {metric.name for metric in metrics},
            {
                "test_counter",
                "test_up_down_counter",
                "test_histogram",
                "test_gauge",
                "test_observable_counter",
                "test_observable_up_down_counter",
                "test_observable_gauge",
            },
        )

    def test_opt_in_histogram_enabled_by_view_preserves_bucket_advisory(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[View(instrument_name="testhistogram", enabled=True)],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
            _opt_in_advisory=True,
        )
        histogram.record(2, {"label": "value"})

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metric = metrics_data.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0))

    def test_opt_in_enabled_by_view_preserves_attributes_advisory(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(instrument_name="opt_in_counter", enabled=True),
                View(instrument_name="opt_in_histogram", enabled=True),
                View(
                    instrument_name="override_counter",
                    enabled=True,
                    attribute_keys={"other"},
                ),
            ],
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter(
            "opt_in_counter",
            _attributes_advisory=["label"],
            _opt_in_advisory=True,
        )
        histogram = meter.create_histogram(
            "opt_in_histogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
            _attributes_advisory=["label"],
            _opt_in_advisory=True,
        )
        override_counter = meter.create_counter(
            "override_counter",
            _attributes_advisory=["label"],
            _opt_in_advisory=True,
        )
        counter.add(1, {"label": "value", "dropped": "value"})
        histogram.record(2, {"label": "value", "dropped": "value"})
        override_counter.add(1, {"label": "value", "other": "value"})

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics_by_name = {metric.name: metric for metric in metrics_data.resource_metrics[0].scope_metrics[0].metrics}
        self.assertEqual(
            dict(metrics_by_name["opt_in_counter"].data.data_points[0].attributes),
            {"label": "value"},
        )
        hist_dp = metrics_by_name["opt_in_histogram"].data.data_points[0]
        self.assertEqual(dict(hist_dp.attributes), {"label": "value"})
        self.assertEqual(hist_dp.explicit_bounds, (1.0, 2.0, 3.0))
        self.assertEqual(
            dict(metrics_by_name["override_counter"].data.data_points[0].attributes),
            {"other": "value"},
        )

    def test_opt_in_enabled_by_view_with_explicit_aggregation(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(
                    instrument_name="last_value_counter",
                    enabled=True,
                    aggregation=LastValueAggregation(),
                ),
                View(
                    instrument_name="dropped_counter",
                    enabled=True,
                    aggregation=DropAggregation(),
                ),
            ],
        )
        meter = meter_provider.get_meter("testmeter")
        last_value_counter = meter.create_counter("last_value_counter", _opt_in_advisory=True)
        dropped_counter = meter.create_counter("dropped_counter", _opt_in_advisory=True)
        last_value_counter.add(3)
        last_value_counter.add(7)
        dropped_counter.add(10)

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "last_value_counter")
        self.assertIsInstance(metrics[0].data, Gauge)
        self.assertEqual(metrics[0].data.data_points[0].value, 7)

    def test_view_enabled_false_disables_default_and_opt_in_instruments(self):
        for opt_in_advisory in (None, False, True):
            with self.subTest(opt_in_advisory=opt_in_advisory):
                reader = InMemoryMetricReader()
                meter_provider = MeterProvider(
                    metric_readers=[reader],
                    views=[
                        View(
                            instrument_name="test_counter",
                            aggregation=SumAggregation(),
                            enabled=False,
                        ),
                        View(instrument_name="test_*", enabled=False),
                    ],
                )
                meter = meter_provider.get_meter("testmeter")

                _create_all_instruments(meter, opt_in_advisory=opt_in_advisory)

                self.assertIsNone(reader.get_metrics_data())

    def test_disable_all_views_and_reenable_selected_instrument(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(instrument_name="*", enabled=False),
                View(instrument_name="enabled_counter", enabled=True),
            ],
        )
        meter = meter_provider.get_meter("testmeter")
        disabled_counter = meter.create_counter("disabled_counter")
        enabled_counter = meter.create_counter("enabled_counter", _opt_in_advisory=True)
        disabled_counter.add(5)
        enabled_counter.add(7)

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "enabled_counter")
        self.assertEqual(metrics[0].data.data_points[0].value, 7)

    def test_invalid_opt_in_advisory_logs_warning_and_defaults_to_enabled(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])
        meter = meter_provider.get_meter("testmeter")

        with self.assertLogs(level=WARNING) as log:
            counter = meter.create_counter(
                "test_counter",
                _opt_in_advisory="invalid",
            )
        self.assertIn("_opt_in_advisory must be a bool", log.output[0])

        with self.assertLogs(level=WARNING) as hist_log:
            histogram = meter.create_histogram(
                "test_histogram",
                explicit_bucket_boundaries_advisory=[1.0, 2.0],
                _opt_in_advisory="invalid",
            )
        self.assertIn("_opt_in_advisory must be a bool", hist_log.output[0])

        counter.add(3)
        histogram.record(1.5)
        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics_by_name = {metric.name: metric for metric in metrics_data.resource_metrics[0].scope_metrics[0].metrics}
        self.assertEqual(set(metrics_by_name), {"test_counter", "test_histogram"})
        self.assertEqual(metrics_by_name["test_counter"].data.data_points[0].value, 3)
        self.assertEqual(metrics_by_name["test_histogram"].data.data_points[0].explicit_bounds, (1.0, 2.0))

    def test_disabled_streams_do_not_retain_per_attribute_aggregations(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[View(instrument_name="view_disabled_counter", enabled=False)],
        )
        meter = meter_provider.get_meter("testmeter")
        opt_in_counter = meter.create_counter("opt_in_counter", _opt_in_advisory=True)
        view_disabled_counter = meter.create_counter("view_disabled_counter")

        for idx in range(10):
            attrs = {"key": f"value_{idx}"}
            opt_in_counter.add(1, attrs)
            view_disabled_counter.add(1, attrs)

        self.assertIsNone(reader.get_metrics_data())

        reader_storage = meter_provider._measurement_consumer._reader_storages[reader]
        matches_by_name = {
            instrument.name: matches
            for instrument, matches in reader_storage._instrument_view_instrument_matches.items()
        }
        self.assertEqual(len(matches_by_name["opt_in_counter"]), 1)
        self.assertEqual(matches_by_name["opt_in_counter"][0]._attributes_aggregation, {})
        self.assertEqual(len(matches_by_name["view_disabled_counter"]), 1)
        self.assertEqual(matches_by_name["view_disabled_counter"][0]._attributes_aggregation, {})
