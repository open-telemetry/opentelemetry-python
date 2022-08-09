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

from math import inf
from typing import Optional, TypeVar, Union

from opentelemetry.sdk.metrics._internal.aggregation import (
    AggregationTemporality,
    _Aggregation,
)
from opentelemetry.sdk.metrics._internal.exponential.buckets import Buckets
from opentelemetry.sdk.metrics._internal.exponential.config import (
    DEFAULT_MAX_SIZE,
    MAX_MAX_SIZE,
    MIN_MAX_SIZE,
)
from opentelemetry.sdk.metrics._internal.exponential.exponent import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential.logarithm_mapping import (
    LogarithmExponentialHistogramMapping,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import Buckets as BucketsPoint
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
)
from opentelemetry.sdk.metrics._internal.point import (
    Histogram as HistogramPoint,
)
from opentelemetry.sdk.metrics._internal.point import (
    HistogramDataPoint,
    NumberDataPoint,
)
from opentelemetry.util.types import Attributes

_DataPointVarT = TypeVar("_DataPointVarT", NumberDataPoint, HistogramDataPoint)


# pylint: disable=protected-access
class _ExponentialBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        attributes: Attributes,
        start_time_unix_nano: int,
        max_size: int = DEFAULT_MAX_SIZE,
    ):
        super().__init__(attributes)
        # maxSize is the maximum capacity of the positive and negative ranges.
        # it is set by Init(), preserved by Copy and Move.)

        if max_size < MIN_MAX_SIZE:
            raise Exception("size {max_size} is smaller than {MIN_MAX_IZE}")

        if max_size > MAX_MAX_SIZE:
            raise Exception("size {max_size} is larter than {MAX_MAX_IZE}")

        self._max_size = max_size

        # sum is the sum of all Updates reflected in the aggregator.  It has
        # the same type number as the corresponding sdkinstrument.Descriptor.
        self._sum = 0

        # count is incremented by 1 per Update.
        self._count = 0

        # zeroCount is incremented by 1 when the measured value is exactly 0.
        self._zero_count = 0

        # min is set when count > 0
        self._min = 0

        # max is set when count > 0
        self._max = 0

        # positive holds the positive values
        self._positive = Buckets()

        # negative holds the negative values by their absolute value
        self._negative = Buckets()

        # mapping corresponds to the current scale, is shared by both positive
        # and negative ranges.

        self._mapping = LogarithmExponentialHistogramMapping(
            LogarithmExponentialHistogramMapping._max_scale
        )
        self._instrument_temporality = AggregationTemporality.DELTA
        self._start_time_unix_nano = start_time_unix_nano

    @property
    def _scale(self):
        if self._count == self._zero_count:
            return 0

        return self._mapping.scale

    def aggregate(self, measurement: Measurement) -> None:
        self._update_by_incr(measurement.value, 1)

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """

        with self._lock:
            if not any(self._negative._counts) and not any(
                self._positive._counts
            ):
                return None

            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            min_ = self._min

            self._negative._counts = [0]
            self._positive._counts = [0]
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._min = inf
            self._max = -inf

        current_point = ExponentialHistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            count=(
                sum(self._negative._counts)
                + sum(self._positive._counts)
                + self._zero_count
            ),
            sum=sum_,
            scale=self._scale,
            zero_count=self._zero_count,
            positive=BucketsPoint(
                self._positive.offset, self._positive._counts
            ),
            negative=BucketsPoint(
                self._negative.offset, self._negative._counts
            ),
            # FIXME: Find the right value for flags
            flags=0,
            min=min_,
            max=max_,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            self._previous_point = current_point
            return current_point

        max_ = current_point.max
        min_ = current_point.min

        if aggregation_temporality is AggregationTemporality.CUMULATIVE:
            start_time_unix_nano = self._previous_point.start_time_unix_nano
            sum_ = current_point.sum + self._previous_point.sum
            # Only update min/max on delta -> cumulative
            max_ = max(current_point.max, self._previous_point.max)
            min_ = min(current_point.min, self._previous_point.min)

            negative_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.negative.bucket_counts,
                    self._previous_point.negative.bucket_counts,
                )
            ]
            positive_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.positive.bucket_counts,
                    self._previous_point.positive.bucket_counts,
                )
            ]
        else:
            start_time_unix_nano = self._previous_point.time_unix_nano
            sum_ = current_point.sum - self._previous_point.sum

            negative_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.negative.bucket_counts,
                    self._previous_point.negative.bucket_counts,
                )
            ]
            positive_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.positive.bucket_counts,
                    self._previous_point.positive.bucket_counts,
                )
            ]

        current_point = ExponentialHistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            count=(
                sum(negative_counts) + sum(positive_counts) + self._zero_count
            ),
            sum=sum_,
            scale=self._scale,
            zero_count=self._zero_count,
            positive=BucketsPoint(self._positive.offset, positive_counts),
            negative=BucketsPoint(self._negative.offset, negative_counts),
            # FIXME: Find the right value for flags
            flags=0,
            min=min_,
            max=max_,
        )

        self._previous_point = current_point
        return current_point

    def _clear(self) -> None:
        self._positive.clear()
        self._negative.clear()
        self._sum = 0
        self._count = 0
        self._zero_count = 0
        self._min = 0
        self._max = 0
        self._mapping = LogarithmExponentialHistogramMapping(
            LogarithmExponentialHistogramMapping._max_scale
        )

    def _swap(self, other: "_ExponentialBucketHistogramAggregation") -> None:

        for attribute in [
            "_positive",
            "_negative",
            "_sum",
            "_count",
            "_zero_count",
            "_min",
            "_max",
            "_mapping",
        ]:
            temp = getattr(self, attribute)
            setattr(self, attribute, getattr(other, attribute))
            setattr(other, attribute, temp)

    def _copy_into(
        self, other: "_ExponentialBucketHistogramAggregation"
    ) -> None:
        other._clear()

        for attribute in [
            "_positive",
            "_negative",
            "_sum",
            "_count",
            "_zero_count",
            "_min",
            "_max",
            "_mapping",
        ]:
            setattr(other, attribute, getattr(self, attribute))

    def _update_by_incr(self, number: Union[int, float], incr: int) -> None:

        value = float(number)

        if self._count == 0:
            self._min = number
            self._max = number

        else:
            if number < self._min:
                self._min = number
            if number > self._max:
                self._max = number

        self._count += incr

        if value == 0:
            self._zero_count += incr
            return

        self._sum += number * incr

        if value > 0:
            buckets = self._positive
        else:
            value = -value
            buckets = self._negative

        self._update(buckets, value, incr)

    def _downscale(self, change: int) -> None:
        """
        Subtracts change from the current mapping scale
        """

        if change == 0:
            return

        if change < 0:
            raise Exception(f"Impossible change of scale: {change}")

        new_scale = self._mapping.scale - change

        self._positive.downscale(change)
        self._negative.downscale(change)

        if new_scale <= 0:
            mapping = ExponentMapping(new_scale)
        else:
            mapping = LogarithmExponentialHistogramMapping(new_scale)

        self._mapping = mapping

    # pylint: disable=no-self-use
    def _change_scale(self, high: int, low: int, size: int) -> int:
        """
        Calculates how much downscaling is needed by shifting the high and low
        values until they are separated by no more than size.
        """

        change = 0

        # FIXME this slightly different from the Go implementation. It should
        # be functionally equal but avoids an infinite loop in certain
        # circumstances (high == 0, low == -1, size == 1).
        while high - low > size:
            high = high >> 1
            low = low >> 1

            change += 1

        if high - low == size:
            high = high >> 1
            low = low >> 1

            change += 1

        return change

    def _update(self, buckets: Buckets, value: float, incr: int) -> None:

        index = self._mapping.map_to_index(value)

        low, high, success = self._increment_index_by(buckets, index, incr)

        if success:
            return

        self._downscale(self._change_scale(high, low, self._max_size))

        index = self._mapping.map_to_index(value)

        _, _, success = self._increment_index_by(buckets, index, incr)

        if not success:
            raise Exception("Downscale logic error")

    def _increment_index_by(
        self, buckets: Buckets, index: int, incr: int
    ) -> tuple:
        """
        Determines if the index lies inside the current range
        [indexStart, indexEnd] and, if not, returns the minimum size (up to
        maxSize) will satisfy the new value.)]

        Returns a tuple: low, high, success
        """

        if incr == 0:
            # Skipping a bunch of work for 0 increment.  This
            # happens when merging sparse data, for example.
            # This also happens UpdateByIncr is used with a 0
            # increment, means it can be safely skipped.

            return 0, 0, True

        if buckets.len() == 0:
            # Go initializes its backing here if it hasn't been done before.
            # I think we don't need to worry about that because the backing
            # has been initialized already.
            buckets._index_start = index
            buckets._index_end = index
            buckets._index_base = index

        elif index < buckets._index_start:
            span = buckets._index_end - index

            if span >= self._max_size:
                # rescaling needed, mapped value to the right

                return index, buckets._index_end, False

            if span >= buckets._backing.size():
                self._grow(buckets, span + 1)

            buckets._index_start = index

        elif index > buckets._index_end:
            span = index - buckets._index_start

            if span >= self._max_size:
                # rescaling needed, mapped value to the right

                return buckets._index_start, index, False

            if span >= buckets._backing.size():

                self._grow(buckets, span + 1)

            buckets._index_end = index

        bucket_index = index - buckets._index_base

        if bucket_index < 0:
            bucket_index += buckets._backing.size()

        buckets.increment_bucket(bucket_index, incr)

        return 0, 0, True

    def _grow(self, buckets: Buckets, needed: int):
        """
        Resizes the backing array by doubling in size up to maxSize.
        this extends the array with a bunch of zeros and copies the
        existing counts to the same position.
        """

        size = buckets._backing.size()
        bias = buckets._index_base - buckets._index_start
        old_positive_limit = size - bias
        new_size = power_of_two_rounded_up(needed)
        if new_size > self._max_size:
            new_size = self._max_size

        new_positive_limit = new_size - bias
        buckets._backing.grow_to(
            new_size, old_positive_limit, new_positive_limit
        )

    def _high_low_at_scale(self, buckets: Buckets, scale: int) -> tuple:
        """
        Returns low, high
        """

        if buckets.len() == 0:
            return 0, -1

        shift = self._scale - scale

        return buckets._index_start >> shift, buckets._index_end >> shift

    def _merge_from(self, other: "_ExponentialBucketHistogramAggregation"):

        if self._count == 0:
            self._min = other._min
            self._max = other._max

        elif other._count != 0:
            if other._min < self._min:
                self._min = other._min
            if other._max > self._max:
                self._max = other._max

        self._sum += other._sum
        self._count += other._count
        self._zero_count += other._zero_count

        min_scale = min(self._scale, other._scale)

        low_positive, high_positive = _with(
            *self._high_low_at_scale(self._positive, min_scale),
            *other._high_low_at_scale(other._positive, min_scale),
        )

        low_negative, high_negative = _with(
            *self._high_low_at_scale(self._negative, min_scale),
            *other._high_low_at_scale(other._negative, min_scale),
        )

        min_scale = min(
            min_scale
            - self._change_scale(high_positive, low_positive, self._max_size),
            min_scale
            - self._change_scale(high_negative, low_negative, self._max_size),
        )

        self._downscale(self._scale - min_scale)

        self._merge_buckets(self._positive, other, other._positive, min_scale)
        self._merge_buckets(self._negative, other, other._negative, min_scale)

    def _merge_buckets(
        self,
        mine: Buckets,
        other: "_ExponentialBucketHistogramAggregation",
        theirs: Buckets,
        scale: int,
    ) -> None:

        their_offset = theirs.offset()
        their_change = other._scale - scale

        for index in range(theirs.len()):

            _, _, success = self._increment_index_by(
                mine, (their_offset + index) >> their_change, theirs.at(index)
            )

            if not success:
                raise Exception("Incorrect merge scale")


def power_of_two_rounded_up(number: int) -> int:
    """
    Computes the least power of two that is >= number.
    """

    number = number - 1
    number |= number >> 1
    number |= number >> 2
    number |= number >> 4
    number |= number >> 8
    number |= number >> 16
    number = number + 1
    return number


def _with(h_low, h_high, o_low, o_high):
    """
    Returns low, high
    """
    if o_low > o_high:
        return h_low, h_high

    if h_low > h_high:
        return o_low, o_high

    return min(h_low, o_low), max(h_high, o_high)
