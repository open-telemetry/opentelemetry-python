# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

from __future__ import annotations

from collections.abc import Iterable
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
    Metric,
    MetricProducer,
    NumberDataPoint,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_TIME_NS = "opentelemetry.sdk.metrics._internal.measurement_consumer.time_ns"


def _make_scope_metrics(name: str, value: int = 7) -> ScopeMetrics:
    return ScopeMetrics(
        scope=InstrumentationScope(name=name),
        metrics=[
            Metric(
                name="produced.metric",
                description="",
                unit="",
                data=Sum(
                    data_points=[
                        NumberDataPoint(
                            attributes={},
                            start_time_unix_nano=0,
                            time_unix_nano=1,
                            value=value,
                        )
                    ],
                    aggregation_temporality=AggregationTemporality.CUMULATIVE,
                    is_monotonic=True,
                ),
            )
        ],
        schema_url="",
    )


def _get_scope_names(metrics_data) -> set[str]:
    names = set()
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            names.add(scope_metrics.scope.name)
    return names


def _find_scope(metrics_data, scope_name: str) -> ScopeMetrics | None:
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            if scope_metrics.scope.name == scope_name:
                return scope_metrics
    return None


def _point_value(scope_metrics: ScopeMetrics, metric_name: str):
    for metric in scope_metrics.metrics:
        if metric.name == metric_name:
            return metric.data.data_points[0].value
    raise AssertionError(f"metric {metric_name!r} not found")


class _FakeProducer(MetricProducer):
    def __init__(
        self, scope_name: str = "fake-producer", value: int = 7
    ) -> None:
        self.produce_calls = 0
        self._scope_name = scope_name
        self._value = value

    def produce(
        self, timeout_millis: float = 10_000
    ) -> Iterable[ScopeMetrics]:
        self.produce_calls += 1
        return [_make_scope_metrics(self._scope_name, self._value)]


class _FailingProducer(MetricProducer):
    def produce(
        self, timeout_millis: float = 10_000
    ) -> Iterable[ScopeMetrics]:
        raise RuntimeError("produce failed")


class _ClockAdvancingProducer(MetricProducer):
    def __init__(self, clock: list[int], advance_ns: int) -> None:
        self._clock = clock
        self._advance_ns = advance_ns
        self.produce_calls = 0

    def produce(
        self, timeout_millis: float = 10_000
    ) -> Iterable[ScopeMetrics]:
        self.produce_calls += 1
        self._clock[0] += self._advance_ns
        return [_make_scope_metrics("slow-producer")]


class TestMetricProducer(TestCase):
    def test_producer_metrics_merged_with_sdk_metrics(self):
        resource = Resource.create({"service.name": "test"})
        producer = _FakeProducer(value=42)
        reader = InMemoryMetricReader(metric_producers=[producer])
        provider = MeterProvider(metric_readers=[reader], resource=resource)

        meter = provider.get_meter("sdk-scope")
        counter: Counter = meter.create_counter("sdk.counter")
        counter.add(1)

        metrics_data = reader.get_metrics_data()

        self.assertEqual(producer.produce_calls, 1)

        self.assertEqual(len(metrics_data.resource_metrics), 1)
        resource_metrics = metrics_data.resource_metrics[0]
        self.assertIs(resource_metrics.resource, resource)
        self.assertEqual(
            resource_metrics.resource.attributes["service.name"], "test"
        )
        self.assertEqual(
            _get_scope_names(metrics_data), {"sdk-scope", "fake-producer"}
        )

        self.assertEqual(
            _point_value(
                _find_scope(metrics_data, "sdk-scope"), "sdk.counter"
            ),
            1,
        )
        self.assertEqual(
            _point_value(
                _find_scope(metrics_data, "fake-producer"), "produced.metric"
            ),
            42,
        )

    def test_producer_only_no_sdk_metrics(self):
        resource = Resource.create({"service.name": "test"})
        producer = _FakeProducer(value=13)
        reader = InMemoryMetricReader(metric_producers=[producer])
        MeterProvider(metric_readers=[reader], resource=resource)

        metrics_data = reader.get_metrics_data()

        self.assertEqual(len(metrics_data.resource_metrics), 1)
        resource_metrics = metrics_data.resource_metrics[0]
        self.assertIs(resource_metrics.resource, resource)
        self.assertEqual(
            resource_metrics.resource.attributes["service.name"], "test"
        )
        self.assertEqual(_get_scope_names(metrics_data), {"fake-producer"})
        self.assertEqual(
            _point_value(
                _find_scope(metrics_data, "fake-producer"), "produced.metric"
            ),
            13,
        )

    def test_multiple_producers(self):
        resource = Resource.create({})
        producers = [
            _FakeProducer("p1", value=1),
            _FakeProducer("p2", value=2),
        ]
        reader = InMemoryMetricReader(metric_producers=producers)
        MeterProvider(metric_readers=[reader], resource=resource)

        metrics_data = reader.get_metrics_data()

        self.assertEqual(_get_scope_names(metrics_data), {"p1", "p2"})
        self.assertEqual(
            _point_value(_find_scope(metrics_data, "p1"), "produced.metric"), 1
        )
        self.assertEqual(
            _point_value(_find_scope(metrics_data, "p2"), "produced.metric"), 2
        )

    def test_no_producers(self):
        reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("sdk-scope")
        meter.create_counter("sdk.counter").add(1)

        metrics_data = reader.get_metrics_data()

        self.assertEqual(_get_scope_names(metrics_data), {"sdk-scope"})

    def test_failing_producer_is_isolated(self):
        resource = Resource.create({})
        good = _FakeProducer("good", value=99)
        reader = InMemoryMetricReader(
            metric_producers=[_FailingProducer(), good]
        )
        provider = MeterProvider(metric_readers=[reader], resource=resource)
        provider.get_meter("sdk-scope").create_counter("sdk.counter").add(1)

        with self.assertLogs(level="WARNING") as cm:
            metrics_data = reader.get_metrics_data()

        self.assertEqual(_get_scope_names(metrics_data), {"sdk-scope", "good"})
        self.assertEqual(good.produce_calls, 1)
        self.assertEqual(
            _point_value(
                _find_scope(metrics_data, "sdk-scope"), "sdk.counter"
            ),
            1,
        )
        self.assertEqual(
            _point_value(_find_scope(metrics_data, "good"), "produced.metric"),
            99,
        )
        self.assertTrue(
            any(
                "failed to produce metrics" in message for message in cm.output
            )
        )

    def test_producer_receives_remaining_timeout_budget(self):
        producer = _FakeProducer()
        reader = InMemoryMetricReader(metric_producers=[producer])
        MeterProvider(metric_readers=[reader])

        # Freeze the clock so the producer receives exactly the full budget.
        with patch.object(
            producer, "produce", wraps=producer.produce
        ) as produce_mock:
            with patch(_TIME_NS, lambda: 0):
                reader.collect(timeout_millis=5_000)

        produce_mock.assert_called_once_with(timeout_millis=5_000)

    def test_timeout_softly_skips_remaining_producers(self):
        clock = [0]
        slow = _ClockAdvancingProducer(clock, advance_ns=int(20 * 1e6))
        never = _FakeProducer("never")
        reader = InMemoryMetricReader(metric_producers=[slow, never])
        MeterProvider(metric_readers=[reader])

        with patch(_TIME_NS, lambda: clock[0]):
            with self.assertLogs(level="WARNING") as cm:
                reader.collect(timeout_millis=10)

        metrics_data = reader._metrics_data
        self.assertEqual(slow.produce_calls, 1)
        self.assertEqual(never.produce_calls, 0)
        self.assertIn("slow-producer", _get_scope_names(metrics_data))
        self.assertEqual(
            _point_value(
                _find_scope(metrics_data, "slow-producer"), "produced.metric"
            ),
            7,
        )
        self.assertTrue(
            any("Timed out collecting" in message for message in cm.output)
        )
