from time import time_ns
from unittest import TestCase

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.metrics._internal.aggregation import (
    _ExplicitBucketHistogramAggregation,
    _LastValueAggregation,
    _SumAggregation,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    SimpleFixedSizeExemplarReservoir,
)
from opentelemetry.sdk.metrics._internal.view import _default_reservoir_factory
from opentelemetry.trace import SpanContext, TraceFlags


class TestSimpleFixedSizeExemplarReservoir(TestCase):
    TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)
    SPAN_ID = int("6e0c63257de34c92", 16)

    def test_no_measurements(self):
        reservoir = SimpleFixedSizeExemplarReservoir(10)
        self.assertEqual(len(reservoir.collect({})), 0)

    def test_has_context(self):
        reservoir = SimpleFixedSizeExemplarReservoir(1)
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)
        reservoir.offer(1, time_ns(), {}, ctx)
        exemplars = reservoir.collect({})
        self.assertEqual(len(exemplars), 1)
        self.assertEqual(exemplars[0].trace_id, self.TRACE_ID)
        self.assertEqual(exemplars[0].span_id, self.SPAN_ID)

    def test_filter_attributes(self):
        reservoir = SimpleFixedSizeExemplarReservoir(1)
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)
        reservoir.offer(
            1, time_ns(), {"key1": "value1", "key2": "value2"}, ctx
        )
        exemplars = reservoir.collect({"key2": "value2"})
        self.assertEqual(len(exemplars), 1)
        self.assertIn("key1", exemplars[0].filtered_attributes)
        self.assertNotIn("key2", exemplars[0].filtered_attributes)

    def test_reset_after_collection(self):
        reservoir = SimpleFixedSizeExemplarReservoir(4)

        reservoir.offer(1.0, time_ns(), {"attribute": "value1"}, Context())
        reservoir.offer(2.0, time_ns(), {"attribute": "value2"}, Context())
        reservoir.offer(3.0, time_ns(), {"attribute": "value3"}, Context())

        exemplars = reservoir.collect({})
        self.assertEqual(len(exemplars), 3)

        # Offer new measurements after reset
        reservoir.offer(4.0, time_ns(), {"attribute": "value4"}, Context())
        reservoir.offer(5.0, time_ns(), {"attribute": "value5"}, Context())

        # Collect again and check the number of exemplars
        new_exemplars = reservoir.collect({})
        self.assertEqual(len(new_exemplars), 2)
        self.assertEqual(new_exemplars[0].value, 4.0)
        self.assertEqual(new_exemplars[1].value, 5.0)


class TestAlignedHistogramBucketExemplarReservoir(TestCase):
    TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)
    SPAN_ID = int("6e0c63257de34c92", 16)

    def test_measurement_in_buckets(self):
        reservoir = AlignedHistogramBucketExemplarReservoir(
            [0, 5, 10, 25, 50, 75]
        )
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)
        reservoir.offer(80, time_ns(), {"bucket": "5"}, ctx)  # outliner
        reservoir.offer(52, time_ns(), {"bucket": "4"}, ctx)
        reservoir.offer(7, time_ns(), {"bucket": "1"}, ctx)
        reservoir.offer(6, time_ns(), {"bucket": "1"}, ctx)

        exemplars = reservoir.collect({"bucket": "1"})

        self.assertEqual(len(exemplars), 3)
        self.assertEqual(exemplars[0].value, 6)
        self.assertEqual(exemplars[1].value, 52)
        self.assertEqual(exemplars[2].value, 80)  # outliner
        self.assertEqual(len(exemplars[0].filtered_attributes), 0)

    def test_last_measurement_in_bucket(self):
        reservoir = AlignedHistogramBucketExemplarReservoir([0, 5, 10, 25])
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace.NonRecordingSpan(span_context)
        ctx = trace.set_span_in_context(span)

        # Offer values to the reservoir
        reservoir.offer(2, time_ns(), {"bucket": "1"}, ctx)  # Bucket 1
        reservoir.offer(7, time_ns(), {"bucket": "2"}, ctx)  # Bucket 2
        reservoir.offer(
            8, time_ns(), {"bucket": "2"}, ctx
        )  # Bucket 2 - should replace the 7
        reservoir.offer(15, time_ns(), {"bucket": "3"}, ctx)  # Bucket 3

        exemplars = reservoir.collect({})

        # Check that each bucket has the correct value
        self.assertEqual(len(exemplars), 3)
        self.assertEqual(exemplars[0].value, 2)
        self.assertEqual(exemplars[1].value, 8)
        self.assertEqual(exemplars[2].value, 15)


class TestExemplarReservoirFactory(TestCase):
    def test_sum_aggregation(self):
        exemplar_reservoir = _default_reservoir_factory(_SumAggregation)
        self.assertEqual(exemplar_reservoir, SimpleFixedSizeExemplarReservoir)

    def test_last_value_aggregation(self):
        exemplar_reservoir = _default_reservoir_factory(_LastValueAggregation)
        self.assertEqual(exemplar_reservoir, SimpleFixedSizeExemplarReservoir)

    def test_explicit_histogram_aggregation(self):
        exemplar_reservoir = _default_reservoir_factory(
            _ExplicitBucketHistogramAggregation
        )
        self.assertEqual(
            exemplar_reservoir, AlignedHistogramBucketExemplarReservoir
        )
