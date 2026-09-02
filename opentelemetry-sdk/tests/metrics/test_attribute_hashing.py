# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Attribute sets that differ in the OTel data model must not share a stream.

`_hash_attributes` builds the aggregation key. Python compares `True == 1 ==
1.0` and hashes them identically, but OTLP encodes them as `bool_value`,
`int_value` and `double_value` -- three different values. Folding them
together merges unrelated time series and mislabels the survivor.
"""

import unittest

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _hash_attributes,
)
from opentelemetry.sdk.metrics.export import InMemoryMetricReader


class TestHashAttributesDistinguishesTypes(unittest.TestCase):
    def test_bool_int_and_float_are_distinct(self):
        keys = [
            _hash_attributes({"k": True}),
            _hash_attributes({"k": 1}),
            _hash_attributes({"k": 1.0}),
        ]
        self.assertEqual(len(set(keys)), 3)

    def test_false_and_zero_are_distinct(self):
        self.assertNotEqual(_hash_attributes({"k": False}), _hash_attributes({"k": 0}))

    def test_none_and_the_string_none_are_distinct(self):
        self.assertNotEqual(_hash_attributes({"k": None}), _hash_attributes({"k": "None"}))

    def test_sequence_of_pairs_and_mapping_are_distinct(self):
        """A list of pairs must not hash like the equivalent mapping."""
        self.assertNotEqual(
            _hash_attributes({"k": (("x", 1),)}),
            _hash_attributes({"k": {"x": 1}}),
        )

    def test_nested_types_are_distinguished(self):
        self.assertNotEqual(_hash_attributes({"k": (True,)}), _hash_attributes({"k": (1,)}))

    def test_key_order_still_does_not_matter(self):
        """Ordering must remain irrelevant; this is the property that matters most."""
        self.assertEqual(
            _hash_attributes({"a": 1, "b": 2}),
            _hash_attributes({"b": 2, "a": 1}),
        )

    def test_equal_attributes_still_share_a_key(self):
        self.assertEqual(_hash_attributes({"a": "x"}), _hash_attributes({"a": "x"}))

    def test_result_is_hashable(self):
        key = _hash_attributes({"a": 1, "b": (1, 2), "c": {"d": None}})
        self.assertIsInstance(hash(key), int)


class TestDistinctAttributeTypesProduceDistinctStreams(unittest.TestCase):
    def setUp(self):
        self.reader = InMemoryMetricReader()
        self.provider = MeterProvider(metric_readers=[self.reader])
        self.meter = self.provider.get_meter(__name__)

    def tearDown(self):
        self.provider.shutdown()

    def _data_points(self):
        data = self.reader.get_metrics_data()
        return data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points

    def test_counter_keeps_bool_int_and_float_apart(self):
        counter = self.meter.create_counter("counter")
        counter.add(1, {"k": True})
        counter.add(1, {"k": 1})
        counter.add(1, {"k": 1.0})

        points = self._data_points()
        self.assertEqual(len(points), 3)
        self.assertEqual([p.value for p in points], [1, 1, 1])
        self.assertEqual(
            sorted(type(dict(p.attributes)["k"]).__name__ for p in points),
            ["bool", "float", "int"],
        )

    def test_histogram_keeps_false_and_zero_apart(self):
        histogram = self.meter.create_histogram("histogram")
        histogram.record(1, {"flag": False})
        histogram.record(2, {"flag": 0})

        points = self._data_points()
        self.assertEqual(len(points), 2)
        self.assertEqual(
            sorted(type(dict(p.attributes)["flag"]).__name__ for p in points),
            ["bool", "int"],
        )

    def test_same_attributes_still_aggregate_together(self):
        counter = self.meter.create_counter("counter")
        counter.add(1, {"k": "same"})
        counter.add(1, {"k": "same"})

        points = self._data_points()
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].value, 2)
