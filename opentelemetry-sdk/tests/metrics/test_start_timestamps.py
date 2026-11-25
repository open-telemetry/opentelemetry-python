# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import concurrent.futures
import os
from itertools import count
from threading import Event
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality, InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    ExponentialBucketHistogramAggregation,
    SumAggregation,
    View,
)


def _metric_by_name(metrics_data, name):
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == name:
                    return metric
    raise AssertionError(f"Metric {name!r} was not collected")


def _points_by_series(metric):
    return {point.attributes["series"]: point for point in metric.data.data_points}


def _series_values(metrics_data, metric_name):
    return {
        series: (point.start_time_unix_nano, point.time_unix_nano, point.value)
        for series, point in _points_by_series(_metric_by_name(metrics_data, metric_name)).items()
    }


def _series_timestamps(metrics_data, metric_name):
    return {
        series: (point.start_time_unix_nano, point.time_unix_nano)
        for series, point in _points_by_series(_metric_by_name(metrics_data, metric_name)).items()
    }


class _AttemptNotifyingLock:
    def __init__(self, lock, attempted):
        self._lock = lock
        self._attempted = attempted

    def __enter__(self):
        self._attempted.set()
        self._lock.acquire()
        return self

    def __exit__(self, *_exc_info):
        self._lock.release()


class TestStartTimestamps(TestCase):
    def test_synchronous_delta_starts_use_instrument_and_reader_boundaries(self):
        reader = InMemoryMetricReader(
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.DELTA,
                Histogram: AggregationTemporality.DELTA,
            }
        )
        exponential_reader = InMemoryMetricReader(
            preferred_aggregation={Histogram: ExponentialBucketHistogramAggregation()},
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.DELTA,
                Histogram: AggregationTemporality.DELTA,
            },
        )

        with patch.dict(os.environ, {"OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED": "false"}):
            provider = MeterProvider(
                metric_readers=[reader, exponential_reader],
                views=[
                    View(instrument_name="counter", name="counter.primary"),
                    View(instrument_name="counter", name="counter.secondary"),
                ],
            )
        self.addCleanup(provider.shutdown)

        instrument_times = iter(
            [
                1_000,  # Counter creation
                1_100,
                1_200,
                2_000,  # UpDownCounter creation
                2_100,
                3_000,  # Histogram creation
                3_100,
                5_100,
                5_200,
                5_300,
                5_400,
            ]
        )
        collection_times = iter([100, 200, 4_000, 5_000, 6_000, 7_000])
        with (
            patch(
                "opentelemetry.sdk.metrics._internal.instrument.time_ns",
                side_effect=instrument_times,
            ),
            patch(
                "opentelemetry.sdk.metrics._internal._view_instrument_match.time_ns",
                return_value=900,
            ),
            patch(
                "opentelemetry.sdk.metrics._internal.metric_reader_storage.time_ns",
                side_effect=collection_times,
            ),
        ):
            meter = provider.get_meter("start-time-tests")

            # These collections happen before instrument creation. The first
            # delta points still start when their instruments are created.
            self.assertIsNone(reader.get_metrics_data())
            self.assertIsNone(exponential_reader.get_metrics_data())

            counter = meter.create_counter("counter")
            counter.add(2, {"series": "first"})
            counter.add(3, {"series": "second"})
            up_down_counter = meter.create_up_down_counter("up-down-counter")
            up_down_counter.add(-4, {"series": "single"})
            histogram = meter.create_histogram("histogram")
            histogram.record(5, {"series": "single"})

            first_reader_data = reader.get_metrics_data()
            first_exponential_data = exponential_reader.get_metrics_data()

            counter.add(7, {"series": "first"})
            counter.add(11, {"series": "second"})
            up_down_counter.add(6, {"series": "single"})
            histogram.record(8, {"series": "single"})

            second_reader_data = reader.get_metrics_data()
            second_exponential_data = exponential_reader.get_metrics_data()

        with self.subTest(metric_name="counter.primary", interval="first"):
            self.assertEqual(
                _series_values(first_reader_data, "counter.primary"),
                {"first": (1_000, 4_000, 2), "second": (1_000, 4_000, 3)},
            )
        with self.subTest(metric_name="counter.primary", interval="second"):
            self.assertEqual(
                _series_values(second_reader_data, "counter.primary"),
                {"first": (4_000, 6_000, 7), "second": (4_000, 6_000, 11)},
            )
        with self.subTest(metric_name="counter.secondary", interval="first"):
            self.assertEqual(
                _series_values(first_reader_data, "counter.secondary"),
                {"first": (1_000, 4_000, 2), "second": (1_000, 4_000, 3)},
            )
        with self.subTest(metric_name="counter.secondary", interval="second"):
            self.assertEqual(
                _series_values(second_reader_data, "counter.secondary"),
                {"first": (4_000, 6_000, 7), "second": (4_000, 6_000, 11)},
            )

        with self.subTest(metric_name="up-down-counter", interval="first"):
            self.assertEqual(_series_values(first_reader_data, "up-down-counter"), {"single": (2_000, 4_000, -4)})
        with self.subTest(metric_name="up-down-counter", interval="second"):
            self.assertEqual(_series_values(second_reader_data, "up-down-counter"), {"single": (4_000, 6_000, 6)})

        with self.subTest(metric_name="histogram", aggregation="explicit", interval="first"):
            self.assertEqual(
                _series_timestamps(first_reader_data, "histogram"),
                {"single": (3_000, 4_000)},
            )
        with self.subTest(metric_name="histogram", aggregation="explicit", interval="second"):
            self.assertEqual(
                _series_timestamps(second_reader_data, "histogram"),
                {"single": (4_000, 6_000)},
            )

        with self.subTest(metric_name="histogram", aggregation="exponential", interval="first"):
            self.assertEqual(
                _series_timestamps(first_exponential_data, "histogram"),
                {"single": (3_000, 5_000)},
            )
        with self.subTest(metric_name="histogram", aggregation="exponential", interval="second"):
            self.assertEqual(
                _series_timestamps(second_exponential_data, "histogram"),
                {"single": (5_000, 7_000)},
            )

    def test_collect_end_time_is_captured_after_storage_lock_acquisition(self):
        # Control the internal lock to reproduce the collection race deterministically.
        # pylint: disable=protected-access
        with patch.dict(os.environ, {"OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED": "false"}):
            reader = InMemoryMetricReader(preferred_temporality={Counter: AggregationTemporality.DELTA})
            provider = MeterProvider(metric_readers=[reader])
        self.addCleanup(provider.shutdown)

        storage = provider._measurement_consumer._reader_storages[reader]
        storage_lock = storage._lock
        lock_attempted = Event()
        storage._lock = _AttemptNotifyingLock(storage_lock, lock_attempted)
        self.addCleanup(setattr, storage, "_lock", storage_lock)

        meter = provider.get_meter("start-time-tests")
        clock = Mock(side_effect=(100, 200, 300))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with (
                patch("opentelemetry.sdk.metrics._internal.instrument.time_ns", clock),
                patch("opentelemetry.sdk.metrics._internal.metric_reader_storage.time_ns", clock),
            ):
                with storage_lock:
                    collection = executor.submit(reader.get_metrics_data)
                    if lock_attempted.wait(timeout=5):
                        counter = meter.create_counter("counter")
                        counter.add(1, {"series": "single"})
                collection_data = collection.result(timeout=5)

        self.assertTrue(lock_attempted.is_set())
        point = _points_by_series(_metric_by_name(collection_data, "counter"))["single"]
        with self.subTest(check="valid interval"):
            self.assertLessEqual(point.start_time_unix_nano, point.time_unix_nano)
            self.assertEqual(point.time_unix_nano, 300)
        with self.subTest(check="measurement retained"):
            self.assertEqual(point.value, 1)

    def test_first_series_after_empty_collection_starts_at_reader_boundary(self):
        with patch.dict(os.environ, {"OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED": "false"}):
            reader = InMemoryMetricReader(
                preferred_aggregation={ObservableCounter: SumAggregation()},
                preferred_temporality={
                    Counter: AggregationTemporality.DELTA,
                    ObservableCounter: AggregationTemporality.CUMULATIVE,
                },
            )
            provider = MeterProvider(metric_readers=[reader])
        self.addCleanup(provider.shutdown)

        callback_has_observed = False

        def callback(_options):
            nonlocal callback_has_observed
            if not callback_has_observed:
                callback_has_observed = True
                return []
            return [Observation(5, attributes={"series": "first"})]

        instrument_clock = count(1_000)
        collection_times = iter([2_000, 3_000])
        with (
            patch(
                "opentelemetry.sdk.metrics._internal.instrument.time_ns",
                side_effect=lambda: next(instrument_clock),
            ),
            patch(
                "opentelemetry.sdk.metrics._internal._view_instrument_match.time_ns",
                return_value=900,
            ),
            patch(
                "opentelemetry.sdk.metrics._internal.metric_reader_storage.time_ns",
                side_effect=collection_times,
            ),
        ):
            meter = provider.get_meter("start-time-tests")
            counter = meter.create_counter("counter")
            meter.create_observable_counter("observable", callbacks=[callback])

            # The instruments exist, but neither has a series when the reader
            # records this boundary. Their first view matches are created next.
            self.assertIsNone(reader.get_metrics_data())

            counter.add(3, {"series": "first"})
            metrics_data = reader.get_metrics_data()

        counter_point = _points_by_series(_metric_by_name(metrics_data, "counter"))["first"]
        observable_point = _points_by_series(_metric_by_name(metrics_data, "observable"))["first"]

        with self.subTest(instrument="Counter"):
            self.assertEqual(
                (counter_point.start_time_unix_nano, counter_point.time_unix_nano, counter_point.value),
                (2_000, 3_000, 3),
            )
        with self.subTest(instrument="ObservableCounter"):
            self.assertEqual(
                (observable_point.start_time_unix_nano, observable_point.time_unix_nano, observable_point.value),
                (2_000, 3_000, 5),
            )

    def test_observable_delta_series_keep_values_across_empty_collections(self):
        for instrument_type in (ObservableCounter, ObservableUpDownCounter):
            with self.subTest(instrument_type=instrument_type.__name__):
                self._assert_observable_series_timestamps(instrument_type, AggregationTemporality.DELTA)

    def test_observable_cumulative_series_keep_their_start_times(self):
        for instrument_type in (ObservableCounter, ObservableUpDownCounter):
            with self.subTest(instrument_type=instrument_type.__name__):
                self._assert_observable_series_timestamps(instrument_type, AggregationTemporality.CUMULATIVE)

    def _assert_observable_series_timestamps(self, instrument_type, temporality):
        reader = InMemoryMetricReader(
            preferred_aggregation={instrument_type: SumAggregation()},
            preferred_temporality={instrument_type: temporality},
        )

        scans = iter(
            [
                [("persistent", 10), ("reappearing", 10)],
                [("late", 5)],
                [],
                [("persistent", 15), ("reappearing", 17), ("late", 9), ("after-gap", 3)],
            ]
        )

        def callback(_options):
            return [Observation(value, attributes={"series": name}) for name, value in next(scans, ())]

        with patch.dict(os.environ, {"OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED": "false"}):
            provider = MeterProvider(metric_readers=[reader])
        self.addCleanup(provider.shutdown)

        instrument_clock = count(10_000)
        collection_times = iter([100, 20_000, 30_000, 40_000, 50_000])
        with (
            patch(
                "opentelemetry.sdk.metrics._internal.instrument.time_ns",
                side_effect=lambda: next(instrument_clock),
            ),
            patch(
                "opentelemetry.sdk.metrics._internal._view_instrument_match.time_ns",
                return_value=9_000,
            ),
            patch(
                "opentelemetry.sdk.metrics._internal.metric_reader_storage.time_ns",
                side_effect=collection_times,
            ),
        ):
            meter = provider.get_meter("start-time-tests")

            self.assertIsNone(reader.get_metrics_data())
            if instrument_type is ObservableCounter:
                meter.create_observable_counter("observable", callbacks=[callback])
            else:
                meter.create_observable_up_down_counter("observable", callbacks=[callback])

            metrics_data = [reader.get_metrics_data() for _ in range(4)]

        self.assertIsNone(metrics_data[2])

        if temporality is AggregationTemporality.DELTA:
            final_expected = {
                "persistent": (40_000, 50_000, 5),
                "reappearing": (40_000, 50_000, 7),
                "late": (40_000, 50_000, 4),
                "after-gap": (40_000, 50_000, 3),
            }
        else:
            final_expected = {
                "persistent": (10_000, 50_000, 15),
                "reappearing": (10_000, 50_000, 17),
                "late": (20_000, 50_000, 9),
                "after-gap": (40_000, 50_000, 3),
            }

        with self.subTest(temporality=temporality, interval="first"):
            self.assertEqual(
                _series_values(metrics_data[0], "observable"),
                {
                    "persistent": (10_000, 20_000, 10),
                    "reappearing": (10_000, 20_000, 10),
                },
            )

        with self.subTest(temporality=temporality, interval="late series"):
            self.assertEqual(
                _series_values(metrics_data[1], "observable"),
                {"late": (20_000, 30_000, 5)},
            )

        with self.subTest(temporality=temporality, interval="after empty collection"):
            self.assertEqual(
                _series_values(metrics_data[3], "observable"),
                final_expected,
            )
