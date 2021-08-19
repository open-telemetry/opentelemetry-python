# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from logging import WARNING
from math import inf
from unittest import TestCase

from opentelemetry.sdk.metrics.aggregator import (
    Aggregator,
    BoundSetAggregator,
    CountAggregator,
    HistogramAggregator,
    LastAggregator,
    MaxAggregator,
    MinAggregator,
    MinMaxSumAggregator,
    MinMaxSumHistogramAggregator,
    SumAggregator,
    _logger,
)


class TestAggregator(TestCase):
    # pylint: disable=no-member

    def test_min_aggregator(self):

        min_aggregator = MinAggregator()

        self.assertEqual(min_aggregator.value, inf)

        min_aggregator.aggregate(3)
        self.assertEqual(min_aggregator.value, 3)

        min_aggregator.aggregate(2)
        self.assertEqual(min_aggregator.value, 2)

        min_aggregator.aggregate(3)
        self.assertEqual(min_aggregator.value, 2)

    def test_max_aggregator(self):

        max_aggregator = MaxAggregator()

        self.assertEqual(max_aggregator.value, -inf)

        max_aggregator.aggregate(2)
        self.assertEqual(max_aggregator.value, 2)

        max_aggregator.aggregate(3)
        self.assertEqual(max_aggregator.value, 3)

        max_aggregator.aggregate(1)
        self.assertEqual(max_aggregator.value, 3)

    def test_sum_aggregator(self):

        sum_aggregator = SumAggregator()

        self.assertEqual(sum_aggregator.value, 0)

        sum_aggregator.aggregate(2)
        self.assertEqual(sum_aggregator.value, 2)

        sum_aggregator.aggregate(3)
        self.assertEqual(sum_aggregator.value, 5)

        sum_aggregator.aggregate(1)
        self.assertEqual(sum_aggregator.value, 6)

    def test_count_aggregator(self):

        count_aggregator = CountAggregator()

        self.assertEqual(count_aggregator.value, 0)

        count_aggregator.aggregate(2)
        self.assertEqual(count_aggregator.value, 1)

        count_aggregator.aggregate(3)
        self.assertEqual(count_aggregator.value, 2)

        count_aggregator.aggregate(1)
        self.assertEqual(count_aggregator.value, 3)

    def test_last_aggregator(self):

        last_aggregator = LastAggregator()

        self.assertEqual(last_aggregator.value, None)

        last_aggregator.aggregate(2)
        self.assertEqual(last_aggregator.value, 2)

        last_aggregator.aggregate(3)
        self.assertEqual(last_aggregator.value, 3)

        last_aggregator.aggregate(2)
        self.assertEqual(last_aggregator.value, 2)

    def test_histogram_aggregator(self):

        histogram_aggregator = HistogramAggregator([-3, 1, 3, 7, 12])

        bucket_0 = histogram_aggregator.value[0]
        bucket_1 = histogram_aggregator.value[1]
        bucket_2 = histogram_aggregator.value[2]
        bucket_3 = histogram_aggregator.value[3]

        self.assertTrue(bucket_0.lower.inclusive)
        self.assertEqual(bucket_0.lower.value, -3)
        self.assertFalse(bucket_0.upper.inclusive)
        self.assertEqual(bucket_0.upper.value, 1)
        self.assertEqual(bucket_0.count, 0)

        self.assertTrue(bucket_1.lower.inclusive)
        self.assertEqual(bucket_1.lower.value, 1)
        self.assertFalse(bucket_1.upper.inclusive)
        self.assertEqual(bucket_1.upper.value, 3)
        self.assertEqual(bucket_1.count, 0)

        self.assertTrue(bucket_2.lower.inclusive)
        self.assertEqual(bucket_2.lower.value, 3)
        self.assertFalse(bucket_2.upper.inclusive)
        self.assertEqual(bucket_2.upper.value, 7)
        self.assertEqual(bucket_2.count, 0)

        self.assertTrue(bucket_3.lower.inclusive)
        self.assertEqual(bucket_3.lower.value, 7)
        self.assertTrue(bucket_3.upper.inclusive)
        self.assertEqual(bucket_3.upper.value, 12)
        self.assertEqual(bucket_3.count, 0)

        histogram_aggregator.aggregate(2)

        self.assertEqual(bucket_0.count, 0)
        self.assertEqual(bucket_1.count, 1)
        self.assertEqual(bucket_2.count, 0)
        self.assertEqual(bucket_3.count, 0)

        histogram_aggregator.aggregate(9)

        self.assertEqual(bucket_0.count, 0)
        self.assertEqual(bucket_1.count, 1)
        self.assertEqual(bucket_2.count, 0)
        self.assertEqual(bucket_3.count, 1)

        histogram_aggregator.aggregate(10)

        self.assertEqual(bucket_0.count, 0)
        self.assertEqual(bucket_1.count, 1)
        self.assertEqual(bucket_2.count, 0)
        self.assertEqual(bucket_3.count, 2)

        histogram_aggregator.aggregate(2)

        self.assertEqual(bucket_0.count, 0)
        self.assertEqual(bucket_1.count, 2)
        self.assertEqual(bucket_2.count, 0)
        self.assertEqual(bucket_3.count, 2)

        histogram_aggregator.aggregate(3)

        self.assertEqual(bucket_0.count, 0)
        self.assertEqual(bucket_1.count, 2)
        self.assertEqual(bucket_2.count, 1)
        self.assertEqual(bucket_3.count, 2)

        histogram_aggregator.aggregate(-3)

        self.assertEqual(bucket_0.count, 1)
        self.assertEqual(bucket_1.count, 2)
        self.assertEqual(bucket_2.count, 1)
        self.assertEqual(bucket_3.count, 2)

        histogram_aggregator.aggregate(12)

        self.assertEqual(bucket_0.count, 1)
        self.assertEqual(bucket_1.count, 2)
        self.assertEqual(bucket_2.count, 1)
        self.assertEqual(bucket_3.count, 3)

        with self.assertLogs(_logger, WARNING) as log:
            print(log.output)
            histogram_aggregator.aggregate(-5)
            self.assertEqual(
                log.output,
                [
                    "WARNING:opentelemetry.sdk.metrics.aggregator:"
                    "Value -5 below lower histogram bound"
                ],
            )

        with self.assertLogs(_logger, WARNING) as log:
            histogram_aggregator.aggregate(13)
            self.assertEqual(
                log.output,
                [
                    "WARNING:opentelemetry.sdk.metrics.aggregator:"
                    "Value 13 over upper histogram bound"
                ],
            )

    def test_min_max_sum_aggregator(self):

        min_max_sum_aggregator = MinMaxSumAggregator()

        self.assertEqual(min_max_sum_aggregator.min.value, inf)
        self.assertEqual(min_max_sum_aggregator.max.value, -inf)
        self.assertEqual(min_max_sum_aggregator.sum.value, 0)

        min_max_sum_aggregator.aggregate(1)
        min_max_sum_aggregator.aggregate(2)
        min_max_sum_aggregator.aggregate(3)

        self.assertEqual(min_max_sum_aggregator.min.value, 1)
        self.assertEqual(min_max_sum_aggregator.max.value, 3)
        self.assertEqual(min_max_sum_aggregator.sum.value, 6)

    def test_min_max_sum_histogram_aggregator(self):

        min_max_sum_histogram_aggregator = MinMaxSumHistogramAggregator(
            [-3, 1, 3, 7, 12]
        )

        self.assertEqual(min_max_sum_histogram_aggregator.min.value, inf)
        self.assertEqual(min_max_sum_histogram_aggregator.max.value, -inf)
        self.assertEqual(min_max_sum_histogram_aggregator.sum.value, 0)

        min_max_sum_histogram_aggregator.aggregate(1)
        min_max_sum_histogram_aggregator.aggregate(2)
        min_max_sum_histogram_aggregator.aggregate(3)

        self.assertEqual(min_max_sum_histogram_aggregator.min.value, 1)
        self.assertEqual(min_max_sum_histogram_aggregator.max.value, 3)
        self.assertEqual(min_max_sum_histogram_aggregator.sum.value, 6)

        bucket_0 = min_max_sum_histogram_aggregator.histogram.value[0]
        bucket_1 = min_max_sum_histogram_aggregator.histogram.value[1]
        bucket_2 = min_max_sum_histogram_aggregator.histogram.value[2]
        bucket_3 = min_max_sum_histogram_aggregator.histogram.value[3]

        self.assertTrue(bucket_0.lower.inclusive)
        self.assertEqual(bucket_0.lower.value, -3)
        self.assertFalse(bucket_0.upper.inclusive)
        self.assertEqual(bucket_0.upper.value, 1)
        self.assertEqual(bucket_0.count, 0)

        self.assertTrue(bucket_1.lower.inclusive)
        self.assertEqual(bucket_1.lower.value, 1)
        self.assertFalse(bucket_1.upper.inclusive)
        self.assertEqual(bucket_1.upper.value, 3)
        self.assertEqual(bucket_1.count, 2)

        self.assertTrue(bucket_2.lower.inclusive)
        self.assertEqual(bucket_2.lower.value, 3)
        self.assertFalse(bucket_2.upper.inclusive)
        self.assertEqual(bucket_2.upper.value, 7)
        self.assertEqual(bucket_2.count, 1)

        self.assertTrue(bucket_3.lower.inclusive)
        self.assertEqual(bucket_3.lower.value, 7)
        self.assertTrue(bucket_3.upper.inclusive)
        self.assertEqual(bucket_3.upper.value, 12)
        self.assertEqual(bucket_3.count, 0)

    def test_boundset_histogram_aggregator(self):
        class BoundSetHistogramAggregator(
            BoundSetAggregator, HistogramAggregator
        ):
            @classmethod
            def _get_value_name(cls):
                return "boundsethistogram"

        bound_set_histogram_aggregator = BoundSetHistogramAggregator(
            1, 4, [6, 9, 11]
        )

        bound_set_histogram_aggregator.aggregate(2)
        bound_set_histogram_aggregator.aggregate(5)
        bound_set_histogram_aggregator.aggregate(10)

        self.assertEqual(
            bound_set_histogram_aggregator.boundset.value, set([2])
        )

        bucket_0 = bound_set_histogram_aggregator.histogram.value[0]
        bucket_1 = bound_set_histogram_aggregator.histogram.value[1]

        self.assertTrue(bucket_0.lower.inclusive)
        self.assertEqual(bucket_0.lower.value, 6)
        self.assertFalse(bucket_0.upper.inclusive)
        self.assertEqual(bucket_0.upper.value, 9)
        self.assertEqual(bucket_0.count, 0)

        self.assertTrue(bucket_1.lower.inclusive)
        self.assertEqual(bucket_1.lower.value, 9)
        self.assertTrue(bucket_1.upper.inclusive)
        self.assertEqual(bucket_1.upper.value, 11)
        self.assertEqual(bucket_1.count, 1)

    def test_histogram_boundset_aggregator(self):
        class HistogramBoundSetAggregator(
            HistogramAggregator, BoundSetAggregator
        ):
            @classmethod
            def _get_value_name(cls):
                return "histogramboundset"

        histogram_bound_set_aggregator = HistogramBoundSetAggregator(
            [6, 9, 11], 1, 4
        )

        histogram_bound_set_aggregator.aggregate(2)
        histogram_bound_set_aggregator.aggregate(5)
        histogram_bound_set_aggregator.aggregate(10)

        self.assertEqual(
            histogram_bound_set_aggregator.boundset.value, set([2])
        )

        bucket_0 = histogram_bound_set_aggregator.histogram.value[0]
        bucket_1 = histogram_bound_set_aggregator.histogram.value[1]

        self.assertTrue(bucket_0.lower.inclusive)
        self.assertEqual(bucket_0.lower.value, 6)
        self.assertFalse(bucket_0.upper.inclusive)
        self.assertEqual(bucket_0.upper.value, 9)
        self.assertEqual(bucket_0.count, 0)

        self.assertTrue(bucket_1.lower.inclusive)
        self.assertEqual(bucket_1.lower.value, 9)
        self.assertTrue(bucket_1.upper.inclusive)
        self.assertEqual(bucket_1.upper.value, 11)
        self.assertEqual(bucket_1.count, 1)

    def test_aggregator_with_args_and_kwargs(self):
        class ArgsAndKwargsAggregator(Aggregator):
            def __init__(
                self,
                self_arg_a,
                self_arg_b,
                self_kwarg_a="a",
                self_kwarg_b="b",
                *parent_args,
                **parent_kwargs
            ):
                self._initialize(
                    ArgsAndKwargsAggregator,
                    (self_arg_a, self_arg_b),
                    {
                        "self_kwarg_a": self_kwarg_a,
                        "self_kwarg_b": self_kwarg_b,
                    },
                    parent_args,
                    parent_kwargs,
                )

            def _add_attributes(
                self,
                self_arg_a,
                self_arg_b,
                self_kwarg_a="a",
                self_kwarg_b="b",
            ):
                self._arg_a = self_arg_a
                self._arg_b = self_arg_b
                self._kwarg_a = self_kwarg_a
                self._kwarg_b = self_kwarg_b
                return super()._add_attributes()

            @classmethod
            def _get_value_name(cls):
                return "args_and_kwargs"

            def _get_initial_value(self):
                return ""

            def _aggregate(self, value):
                return "".join(
                    [
                        self._arg_a,
                        self._arg_b,
                        self._kwarg_a,
                        self._kwarg_b,
                        value,
                    ]
                )

        args_and_kwargs_aggregator = ArgsAndKwargsAggregator(
            "a", "b", self_kwarg_a="c", self_kwarg_b="d"
        )

        args_and_kwargs_aggregator.aggregate("e")

        self.assertEqual(args_and_kwargs_aggregator.value, "abcde")
