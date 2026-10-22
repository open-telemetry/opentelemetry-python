# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access
from threading import Thread
from unittest import TestCase

from opentelemetry.metrics import NoOpMeterProvider, Observation
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import View

_OVERFLOW = "otel.metric.overflow"


def _data_points(reader):
    metrics = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics
    return metrics[0].data.data_points


def _overflow_points(data_points):
    return [point for point in data_points if _OVERFLOW in point.attributes]


class TestCardinalityLimit(TestCase):
    @staticmethod
    def _create(reader, views=()):
        reader._set_meter_provider(NoOpMeterProvider())
        return MeterProvider(metric_readers=[reader], views=list(views))

    def test_default_limit_is_2000(self):
        reader = InMemoryMetricReader()
        counter = self._create(reader).get_meter("m").create_counter("c")

        for index in range(2500):
            counter.add(1, {"k": index})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 2000)
        self.assertEqual(sum(point.value for point in data_points), 2500)
        overflow = _overflow_points(data_points)
        self.assertEqual(len(overflow), 1)
        self.assertEqual(dict(overflow[0].attributes), {_OVERFLOW: True})
        self.assertEqual(overflow[0].value, 2500 - 1999)

    def test_no_overflow_below_limit(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 5})
        counter = self._create(reader).get_meter("m").create_counter("c")

        for index in range(4):
            counter.add(1, {"k": index})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 4)
        self.assertEqual(_overflow_points(data_points), [])

    def test_reader_limit_per_instrument_class(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 3})
        meter = self._create(reader).get_meter("m")
        counter = meter.create_counter("counter")
        histogram = meter.create_histogram("histogram")

        for index in range(10):
            counter.add(1, {"k": index})
            histogram.record(1, {"k": index})

        metrics = {
            metric.name: metric for metric in reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics
        }
        self.assertEqual(len(metrics["counter"].data.data_points), 3)
        self.assertEqual(len(metrics["histogram"].data.data_points), 10)

    def test_view_limit_overrides_reader_limit(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 3})
        view = View(instrument_name="c", aggregation_cardinality_limit=6)
        counter = self._create(reader, [view]).get_meter("m").create_counter("c")

        for index in range(10):
            counter.add(1, {"k": index})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 6)
        self.assertEqual(sum(point.value for point in data_points), 10)

    def test_limit_of_one_aggregates_everything_into_overflow(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 1})
        counter = self._create(reader).get_meter("m").create_counter("c")

        for index in range(5):
            counter.add(2, {"k": index})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 1)
        self.assertEqual(dict(data_points[0].attributes), {_OVERFLOW: True})
        self.assertEqual(data_points[0].value, 10)

    def test_limit_applies_after_attribute_filtering(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 3})
        view = View(instrument_name="c", attribute_keys={"keep"})
        counter = self._create(reader, [view]).get_meter("m").create_counter("c")

        for index in range(10):
            counter.add(1, {"keep": index % 2, "drop": index})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 2)
        self.assertEqual(_overflow_points(data_points), [])

    def test_cumulative_keeps_sets_observed_before_overflow(self):
        reader = InMemoryMetricReader(cardinality_limits={Counter: 3})
        counter = self._create(reader).get_meter("m").create_counter("c")

        counter.add(1, {"k": "a"})
        counter.add(1, {"k": "b"})
        counter.add(1, {"k": "c"})
        counter.add(1, {"k": "d"})
        counter.add(1, {"k": "a"})
        counter.add(1, {"k": "e"})

        data_points = _data_points(reader)
        by_attributes = {tuple(sorted(point.attributes.items())): point.value for point in data_points}
        self.assertEqual(
            by_attributes,
            {
                (("k", "a"),): 2,
                (("k", "b"),): 1,
                ((_OVERFLOW, True),): 3,
            },
        )

        # The sets that were present before overflow are still exported.
        counter.add(1, {"k": "c"})
        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 3)
        self.assertEqual(sum(point.value for point in data_points), 7)

    def test_delta_limit_resets_every_collection(self):
        reader = InMemoryMetricReader(
            preferred_temporality={Counter: AggregationTemporality.DELTA},
            cardinality_limits={Counter: 3},
        )
        counter = self._create(reader).get_meter("m").create_counter("c")

        for cycle in range(3):
            for index in range(6):
                counter.add(1, {"k": f"{cycle}-{index}"})

            data_points = _data_points(reader)
            with self.subTest(cycle=cycle):
                self.assertEqual(len(data_points), 3)
                self.assertEqual(sum(point.value for point in data_points), 6)
                self.assertEqual(len(_overflow_points(data_points)), 1)

    def test_delta_idle_sets_are_not_exported_or_counted(self):
        reader = InMemoryMetricReader(
            preferred_temporality={Counter: AggregationTemporality.DELTA},
            cardinality_limits={Counter: 3},
        )
        counter = self._create(reader).get_meter("m").create_counter("c")

        counter.add(1, {"k": "a"})
        counter.add(1, {"k": "b"})
        _data_points(reader)

        counter.add(1, {"k": "c"})
        counter.add(1, {"k": "d"})
        data_points = _data_points(reader)

        self.assertEqual(len(data_points), 2)
        self.assertEqual(_overflow_points(data_points), [])

    def test_delta_concurrent_measurements_are_not_lost(self):
        reader = InMemoryMetricReader(
            preferred_temporality={Counter: AggregationTemporality.DELTA},
            cardinality_limits={Counter: 10},
        )
        counter = self._create(reader).get_meter("m").create_counter("c")
        measurements_per_thread = 2000

        def record():
            for index in range(measurements_per_thread):
                counter.add(1, {"k": index % 50})

        threads = [Thread(target=record) for _ in range(4)]
        for thread in threads:
            thread.start()

        total = 0
        while any(thread.is_alive() for thread in threads):
            total += sum(point.value for point in _data_points_or_empty(reader))
        for thread in threads:
            thread.join()
        total += sum(point.value for point in _data_points_or_empty(reader))

        self.assertEqual(total, 4 * measurements_per_thread)

    def test_asynchronous_instrument_prefers_first_observed(self):
        def callback(options):
            for index in range(6):
                yield Observation(index, {"k": index})

        reader = InMemoryMetricReader(cardinality_limits={ObservableCounter: 3})
        meter = self._create(reader).get_meter("m")
        meter.create_observable_counter("oc", callbacks=[callback])

        data_points = _data_points(reader)
        by_attributes = {tuple(sorted(point.attributes.items())): point.value for point in data_points}
        self.assertEqual(
            by_attributes,
            {
                (("k", 0),): 0,
                (("k", 1),): 1,
                ((_OVERFLOW, True),): 2 + 3 + 4 + 5,
            },
        )

    def test_asynchronous_delta_conversion_survives_collection(self):
        values = iter([10, 25])

        def callback(options):
            yield Observation(next(values, 0), {"k": "a"})

        reader = InMemoryMetricReader(
            preferred_temporality={ObservableCounter: AggregationTemporality.DELTA},
            cardinality_limits={ObservableCounter: 3},
        )
        self._create(reader).get_meter("m").create_observable_counter("oc", callbacks=[callback])

        self.assertEqual(_data_points(reader)[0].value, 10)
        self.assertEqual(_data_points(reader)[0].value, 15)

    def test_histogram_overflow(self):
        reader = InMemoryMetricReader(cardinality_limits={Histogram: 2})
        histogram = self._create(reader).get_meter("m").create_histogram("h")

        histogram.record(1, {"k": "a"})
        histogram.record(2, {"k": "b"})
        histogram.record(3, {"k": "c"})

        data_points = _data_points(reader)
        self.assertEqual(len(data_points), 2)
        overflow = _overflow_points(data_points)
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0].count, 2)
        self.assertEqual(overflow[0].sum, 5)


def _data_points_or_empty(reader):
    data = reader.get_metrics_data()
    if data is None:
        return []
    return data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points
