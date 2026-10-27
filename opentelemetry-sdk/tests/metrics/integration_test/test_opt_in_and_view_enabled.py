# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import WARNING
from unittest import TestCase

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
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
                _opt_in_advisory="invalid",  # type: ignore[arg-type]
            )
        self.assertIn("_opt_in_advisory must be a bool", log.output[0])

        counter.add(3)
        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metrics = metrics_data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "test_counter")
        self.assertEqual(metrics[0].data.data_points[0].value, 3)
