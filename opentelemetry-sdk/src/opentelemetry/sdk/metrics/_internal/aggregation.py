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

# pylint: disable=too-many-lines

from abc import ABC, abstractmethod
from bisect import bisect_left
from enum import IntEnum
from logging import getLogger
from math import inf
from threading import Lock
from typing import Generic, List, Optional, Sequence, TypeVar

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    Histogram,
    Instrument,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    Synchronous,
    UpDownCounter,
    _Gauge,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.buckets import (
    Buckets,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping import (
    Mapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.exponent_mapping import (
    ExponentMapping,
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import Buckets as BucketsPoint
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogramDataPoint,
)
from opentelemetry.sdk.metrics._internal.point import Gauge as GaugePoint
from opentelemetry.sdk.metrics._internal.point import (
    Histogram as HistogramPoint,
)
from opentelemetry.sdk.metrics._internal.point import (
    HistogramDataPoint,
    NumberDataPoint,
    Sum,
)
from opentelemetry.util.types import Attributes

_DataPointVarT = TypeVar("_DataPointVarT", NumberDataPoint, HistogramDataPoint)

_logger = getLogger(__name__)


class AggregationTemporality(IntEnum):
    """
    The temporality to use when aggregating data.

    Can be one of the following values:
    """

    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


class _Aggregation(ABC, Generic[_DataPointVarT]):
    def __init__(self, attributes: Attributes):
        self._lock = Lock()
        self._attributes = attributes
        self._previous_point = None

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _DropAggregation(_Aggregation):
    def aggregate(self, measurement: Measurement) -> None:
        pass

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _SumAggregation(_Aggregation[Sum]):
    def __init__(
        self,
        attributes: Attributes,
        instrument_is_monotonic: bool,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
    ):
        super().__init__(attributes)

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_aggregation_temporality = (
            instrument_aggregation_temporality
        )
        self._instrument_is_monotonic = instrument_is_monotonic

        self._current_value = None

        self._previous_collection_start_nano = self._start_time_unix_nano
        self._previous_cumulative_value = 0

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            if self._current_value is None:
                self._current_value = 0

            self._current_value = self._current_value + measurement.value

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[NumberDataPoint]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.

        Synchronous instruments have a method which is called directly with
        increments for a given quantity:

        For example, an instrument that counts the amount of passengers in
        every vehicle that crosses a certain point in a highway:

        synchronous_instrument.add(2)
        collect(...)  # 2 passengers are counted
        synchronous_instrument.add(3)
        collect(...)  # 3 passengers are counted
        synchronous_instrument.add(1)
        collect(...)  # 1 passenger is counted

        In this case the instrument aggregation temporality is DELTA because
        every value represents an increment to the count,

        Asynchronous instruments have a callback which returns the total value
        of a given quantity:

        For example, an instrument that measures the amount of bytes written to
        a certain hard drive:

        callback() -> 1352
        collect(...) # 1352 bytes have been written so far
        callback() -> 2324
        collect(...) # 2324 bytes have been written so far
        callback() -> 4542
        collect(...) # 4542 bytes have been written so far

        In this case the instrument aggregation temporality is CUMULATIVE
        because every value represents the total of the measurement.

        There is also the collection aggregation temporality, which is passed
        to this method. The collection aggregation temporality defines the
        nature of the returned value by this aggregation.

        When the collection aggregation temporality matches the
        instrument aggregation temporality, then this method returns the
        current value directly:

        synchronous_instrument.add(2)
        collect(DELTA) -> 2
        synchronous_instrument.add(3)
        collect(DELTA) -> 3
        synchronous_instrument.add(1)
        collect(DELTA) -> 1

        callback() -> 1352
        collect(CUMULATIVE) -> 1352
        callback() -> 2324
        collect(CUMULATIVE) -> 2324
        callback() -> 4542
        collect(CUMULATIVE) -> 4542

        When the collection aggregation temporality does not match the
        instrument aggregation temporality, then a conversion is made. For this
        purpose, this aggregation keeps a private attribute,
        self._previous_cumulative.

        When the instrument is synchronous:

        self._previous_cumulative_value is the sum of every previously
        collected (delta) value. In this case, the returned (cumulative) value
        will be:

        self._previous_cumulative_value + current_value

        synchronous_instrument.add(2)
        collect(CUMULATIVE) -> 2
        synchronous_instrument.add(3)
        collect(CUMULATIVE) -> 5
        synchronous_instrument.add(1)
        collect(CUMULATIVE) -> 6

        Also, as a diagram:

        time ->

        self._previous_cumulative_value
        |-------------|

        current_value (delta)
                      |----|

        returned value (cumulative)
        |------------------|

        When the instrument is asynchronous:

        self._previous_cumulative_value is the value of the previously
        collected (cumulative) value. In this case, the returned (delta) value
        will be:

        current_value - self._previous_cumulative_value

        callback() -> 1352
        collect(DELTA) -> 1352
        callback() -> 2324
        collect(DELTA) -> 972
        callback() -> 4542
        collect(DELTA) -> 2218

        Also, as a diagram:

        time ->

        self._previous_cumulative_value
        |-------------|

        current_value (cumulative)
        |------------------|

        returned value (delta)
                      |----|
        """

        with self._lock:
            current_value = self._current_value
            self._current_value = None

            if (
                self._instrument_aggregation_temporality
                is AggregationTemporality.DELTA
            ):
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if (
                    collection_aggregation_temporality
                    is AggregationTemporality.DELTA
                ):

                    previous_collection_start_nano = (
                        self._previous_collection_start_nano
                    )
                    self._previous_collection_start_nano = (
                        collection_start_nano
                    )

                    if current_value is None:
                        return None

                    return NumberDataPoint(
                        attributes=self._attributes,
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        value=current_value,
                    )

                if current_value is None:
                    current_value = 0

                self._previous_cumulative_value = (
                    current_value + self._previous_cumulative_value
                )

                return NumberDataPoint(
                    attributes=self._attributes,
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    value=self._previous_cumulative_value,
                )

            # This happens when the corresponding instrument for this
            # aggregation is asynchronous.

            if current_value is None:
                # This happens when the corresponding instrument callback
                # does not produce measurements.
                return None

            if (
                collection_aggregation_temporality
                is AggregationTemporality.DELTA
            ):
                result_value = current_value - self._previous_cumulative_value

                self._previous_cumulative_value = current_value

                previous_collection_start_nano = (
                    self._previous_collection_start_nano
                )
                self._previous_collection_start_nano = collection_start_nano

                return NumberDataPoint(
                    attributes=self._attributes,
                    start_time_unix_nano=previous_collection_start_nano,
                    time_unix_nano=collection_start_nano,
                    value=result_value,
                )

            return NumberDataPoint(
                attributes=self._attributes,
                start_time_unix_nano=self._start_time_unix_nano,
                time_unix_nano=collection_start_nano,
                value=current_value,
            )


class _LastValueAggregation(_Aggregation[GaugePoint]):
    def __init__(self, attributes: Attributes):
        super().__init__(attributes)
        self._value = None

    def aggregate(self, measurement: Measurement):
        with self._lock:
            self._value = measurement.value

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if self._value is None:
                return None
            value = self._value
            self._value = None

        return NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=None,
            time_unix_nano=collection_start_nano,
            value=value,
        )


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        attributes: Attributes,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ):
        super().__init__(attributes)

        self._boundaries = tuple(boundaries)
        self._record_min_max = record_min_max
        self._min = inf
        self._max = -inf
        self._sum = 0

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_aggregation_temporality = (
            instrument_aggregation_temporality
        )

        self._current_value = None

        self._previous_collection_start_nano = self._start_time_unix_nano
        self._previous_cumulative_value = self._get_empty_bucket_counts()
        self._previous_min = inf
        self._previous_max = -inf
        self._previous_sum = 0

    def _get_empty_bucket_counts(self) -> List[int]:
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            if self._current_value is None:
                self._current_value = self._get_empty_bucket_counts()

            value = measurement.value

            self._sum += value

            if self._record_min_max:
                self._min = min(self._min, value)
                self._max = max(self._max, value)

            self._current_value[bisect_left(self._boundaries, value)] += 1

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """

        with self._lock:
            current_value = self._current_value
            sum_ = self._sum
            min_ = self._min
            max_ = self._max

            self._current_value = None
            self._sum = 0
            self._min = inf
            self._max = -inf

            if (
                self._instrument_aggregation_temporality
                is AggregationTemporality.DELTA
            ):
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if (
                    collection_aggregation_temporality
                    is AggregationTemporality.DELTA
                ):

                    previous_collection_start_nano = (
                        self._previous_collection_start_nano
                    )
                    self._previous_collection_start_nano = (
                        collection_start_nano
                    )

                    if current_value is None:
                        return None

                    return HistogramDataPoint(
                        attributes=self._attributes,
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        count=sum(current_value),
                        sum=sum_,
                        bucket_counts=tuple(current_value),
                        explicit_bounds=self._boundaries,
                        min=min_,
                        max=max_,
                    )

                if current_value is None:
                    current_value = self._get_empty_bucket_counts()

                self._previous_cumulative_value = [
                    current_value_element + previous_cumulative_value_element
                    for (
                        current_value_element,
                        previous_cumulative_value_element,
                    ) in zip(current_value, self._previous_cumulative_value)
                ]
                self._previous_min = min(min_, self._previous_min)
                self._previous_max = max(max_, self._previous_max)
                self._previous_sum = sum_ + self._previous_sum

                return HistogramDataPoint(
                    attributes=self._attributes,
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    count=sum(self._previous_cumulative_value),
                    sum=self._previous_sum,
                    bucket_counts=tuple(self._previous_cumulative_value),
                    explicit_bounds=self._boundaries,
                    min=self._previous_min,
                    max=self._previous_max,
                )

            return None


# pylint: disable=protected-access
class _ExponentialBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    # _min_max_size and _max_max_size are the smallest and largest values
    # the max_size parameter may have, respectively.

    # _min_max_size is is the smallest reasonable value which is small enough
    # to contain the entire normal floating point range at the minimum scale.
    _min_max_size = 2

    # _max_max_size is an arbitrary limit meant to limit accidental creation of
    # giant exponential bucket histograms.
    _max_max_size = 16384

    def __init__(
        self,
        attributes: Attributes,
        instrument_aggregation_temporality: AggregationTemporality,
        start_time_unix_nano: int,
        # This is the default maximum number of buckets per positive or
        # negative number range.  The value 160 is specified by OpenTelemetry.
        # See the derivation here:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exponential-bucket-histogram-aggregation)
        max_size: int = 160,
        max_scale: int = 20,
    ):
        # max_size is the maximum capacity of the positive and negative
        # buckets.
        # _sum is the sum of all the values aggregated by this aggregator.
        # _count is the count of all calls to aggregate.
        # _zero_count is the count of all the calls to aggregate when the value
        # to be aggregated is exactly 0.
        # _min is the smallest value aggregated by this aggregator.
        # _max is the smallest value aggregated by this aggregator.
        # _positive holds the positive values.
        # _negative holds the negative values by their absolute value.
        if max_size < self._min_max_size:
            raise ValueError(
                f"Buckets max size {max_size} is smaller than "
                "minimum max size {self._min_max_size}"
            )

        if max_size > self._max_max_size:
            raise ValueError(
                f"Buckets max size {max_size} is larger than "
                "maximum max size {self._max_max_size}"
            )
        if max_scale > 20:
            _logger.warning(
                "max_scale is set to %s which is "
                "larger than the recommended value of 20",
                max_scale,
            )

        super().__init__(attributes)

        self._max_size = max_size
        self._max_scale = max_scale
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._count = 0
        self._zero_count = 0

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_aggregation_temporality = (
            instrument_aggregation_temporality
        )

        self._current_value_positive = None
        self._current_value_negative = None

        self._previous_collection_start_nano = self._start_time_unix_nano
        self._previous_cumulative_value_positive = None
        self._previous_cumulative_value_negative = None
        self._previous_min = inf
        self._previous_max = -inf
        self._previous_sum = 0
        self._previous_count = 0
        self._previous_zero_count = 0

        self._mapping = self._new_exponential_mapping(self._max_scale)

        self._previous_scale = None

    def aggregate(self, measurement: Measurement) -> None:
        # pylint: disable=too-many-branches,too-many-statements, too-many-locals

        with self._lock:

            value = measurement.value

            if self._current_value_positive is None:
                self._current_value_positive = Buckets()
            if self._current_value_negative is None:
                self._current_value_negative = Buckets()

            if value < self._min:
                self._min = value

            if value > self._max:
                self._max = value

            if value == 0:
                self._zero_count += 1
                return

            elif value > 0:
                current_value = self._current_value_positive

            else:
                value = -value
                current_value = self._current_value_negative

            self._sum += value

            self._count += 1

            index = self._mapping.map_to_index(value)

            is_rescaling_needed = False
            low, high = 0, 0

            if len(current_value) == 0:
                current_value.index_start = index
                current_value.index_end = index
                current_value.index_base = index

            elif (
                index < current_value.index_start
                and (current_value.index_end - index) >= self._max_size
            ):
                is_rescaling_needed = True
                low = index
                high = current_value.index_end

            elif (
                index > current_value.index_end
                and (index - current_value.index_start) >= self._max_size
            ):
                is_rescaling_needed = True
                low = current_value.index_start
                high = index

            if is_rescaling_needed:

                scale_change = self._get_scale_change(low, high)
                self._downscale(
                    scale_change,
                    self._current_value_positive,
                    self._current_value_negative,
                )
                new_scale = self._mapping.scale - scale_change
                self._mapping = self._new_exponential_mapping(new_scale)

                index = self._mapping.map_to_index(value)

            if index < current_value.index_start:
                span = current_value.index_end - index

                if span >= len(current_value.counts):
                    current_value.grow(span + 1, self._max_size)

                current_value.index_start = index

            elif index > current_value.index_end:
                span = index - current_value.index_start

                if span >= len(current_value.counts):
                    current_value.grow(span + 1, self._max_size)

                current_value.index_end = index

            bucket_index = index - current_value.index_base

            if bucket_index < 0:
                bucket_index += len(current_value.counts)

            current_value.increment_bucket(bucket_index)

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        # pylint: disable=too-many-statements, too-many-locals
        with self._lock:
            current_value_positive = self._current_value_positive
            current_value_negative = self._current_value_negative
            sum_ = self._sum
            min_ = self._min
            max_ = self._max
            count = self._count
            zero_count = self._zero_count
            if self._count == self._zero_count:
                scale = 0
            else:
                scale = self._mapping.scale

            self._current_value_positive = None
            self._current_value_negative = None
            self._sum = 0
            self._min = inf
            self._max = -inf
            self._count = 0
            self._zero_count = 0

            if (
                self._instrument_aggregation_temporality
                is AggregationTemporality.DELTA
            ):
                # This happens when the corresponding instrument for this
                # aggregation is synchronous.
                if (
                    collection_aggregation_temporality
                    is AggregationTemporality.DELTA
                ):

                    if (
                        current_value_positive is None and
                        current_value_negative is None
                    ):
                        return None

                    previous_collection_start_nano = (
                        self._previous_collection_start_nano
                    )
                    self._previous_collection_start_nano = (
                        collection_start_nano
                    )

                    return ExponentialHistogramDataPoint(
                        attributes=self._attributes,
                        start_time_unix_nano=previous_collection_start_nano,
                        time_unix_nano=collection_start_nano,
                        count=count,
                        sum=sum_,
                        scale=scale,
                        zero_count=zero_count,
                        positive=BucketsPoint(
                            offset=current_value_positive.offset,
                            bucket_counts=(
                                current_value_positive.get_offset_counts()
                            ),
                        ),
                        negative=BucketsPoint(
                            offset=current_value_negative.offset,
                            bucket_counts=(
                                current_value_negative.get_offset_counts()
                            ),
                        ),
                        # FIXME: Find the right value for flags
                        flags=0,
                        min=min_,
                        max=max_,
                    )

                # Here collection_temporality is CUMULATIVE.
                # instrument_temporality is always DELTA for the time being.
                # Here we need to handle the case where:
                # collect is called after at least one other call to collect
                # (there is data in previous buckets, a call to merge is needed
                # to handle possible differences in bucket sizes).
                # collect is called without another call previous call to
                # collect was made (there is no previous buckets, previous,
                # empty buckets that are the same scale of the current buckets
                # need to be made so that they can be cumulatively aggregated
                # to the current buckets).

                # TODO, implement this case

                if current_value_positive is None:
                    current_value_positive = Buckets()
                if current_value_negative is None:
                    current_value_negative = Buckets()
                if self._previous_scale is None:
                    self._previous_scale = scale

                if self._previous_cumulative_value_positive is None:
                    self._previous_cumulative_value_positive = (
                        current_value_positive.copy_empty()
                    )
                if self._previous_cumulative_value_negative is None:
                    self._previous_cumulative_value_negative = (
                        current_value_negative.copy_empty()
                    )

                min_scale = min(self._previous_scale, scale)

                low_positive, high_positive = (
                    self._get_low_high_previous_current(
                        self._previous_cumulative_value_positive,
                        current_value_positive,
                        scale,
                        min_scale,
                    )
                )
                # running test_aggregate_collect in 3.11
                # low_positive == 1048575
                # high_positive == 1048575
                low_negative, high_negative = (
                    self._get_low_high_previous_current(
                        self._previous_cumulative_value_negative,
                        current_value_negative,
                        scale,
                        min_scale,
                    )
                )
                # low_negative == 0
                # high_negative == -1

                min_scale = min(
                    min_scale
                    - self._get_scale_change(low_positive, high_positive),
                    min_scale
                    - self._get_scale_change(low_negative, high_negative),
                )

                # FIXME Go implementation checks if the histogram (not the mapping
                # but the histogram) has a count larger than zero, if not, scale
                # (the histogram scale) would be zero. See exponential.go 191
                self._downscale(
                    self._previous_scale - min_scale,
                    self._previous_cumulative_value_positive,
                    self._previous_cumulative_value_negative,
                )
                self._merge(
                    self._previous_cumulative_value_positive,
                    current_value_positive,
                    scale,
                    min_scale,
                    collection_aggregation_temporality,
                )
                self._merge(
                    self._previous_cumulative_value_negative,
                    current_value_negative,
                    scale,
                    min_scale,
                    collection_aggregation_temporality,
                )

                self._previous_scale = min_scale

                self._previous_cumulative_value_positive = (
                    current_value_positive
                )
                self._previous_cumulative_value_negative = (
                    current_value_negative
                )
                self._previous_min = min(min_, self._previous_min)
                self._previous_max = max(max_, self._previous_max)
                self._previous_sum = sum_ + self._previous_sum
                self._previous_count = count + self._previous_count
                self._previous_zero_count = (
                    zero_count + self._previous_zero_count
                )

                return ExponentialHistogramDataPoint(
                    attributes=self._attributes,
                    start_time_unix_nano=self._start_time_unix_nano,
                    time_unix_nano=collection_start_nano,
                    count=self._previous_count,
                    sum=self._previous_sum,
                    scale=scale,
                    zero_count=self._previous_zero_count,
                    positive=BucketsPoint(
                        offset=current_value_positive.offset,
                        bucket_counts=current_value_positive.get_offset_counts(),
                    ),
                    negative=BucketsPoint(
                        offset=current_value_negative.offset,
                        bucket_counts=current_value_negative.get_offset_counts(),
                    ),
                    # FIXME: Find the right value for flags
                    flags=0,
                    min=min_,
                    max=max_,
                )

            return None

    def _get_low_high_previous_current(
        self,
        previous_point_buckets,
        current_point_buckets,
        current_scale,
        min_scale,
    ):

        (previous_point_low, previous_point_high) = self._get_low_high(
            previous_point_buckets, self._previous_scale, min_scale
        )
        (current_point_low, current_point_high) = self._get_low_high(
            current_point_buckets, current_scale, min_scale
        )

        if current_point_low > current_point_high:
            low = previous_point_low
            high = previous_point_high

        elif previous_point_low > previous_point_high:
            low = current_point_low
            high = current_point_high

        else:
            low = min(previous_point_low, current_point_low)
            high = max(previous_point_high, current_point_high)

        return low, high

    @staticmethod
    def _get_low_high(buckets, scale, min_scale):
        if buckets.counts == [0]:
            return 0, -1

        shift = scale - min_scale

        return buckets.index_start >> shift, buckets.index_end >> shift

    @staticmethod
    def _new_exponential_mapping(scale: int) -> Mapping:
        if scale <= 0:
            return ExponentMapping(scale)
        return LogarithmMapping(scale)

    def _get_scale_change(self, low, high):

        change = 0

        while high - low >= self._max_size:
            high = high >> 1
            low = low >> 1

            change += 1

        return change

    @staticmethod
    def _downscale(change: int, positive, negative):

        if change == 0:
            return

        if change < 0:
            # pylint: disable=broad-exception-raised
            raise Exception("Invalid change of scale")

        positive.downscale(change)
        negative.downscale(change)

    def _merge(
        self,
        previous_buckets: Buckets,
        current_buckets: Buckets,
        current_scale,
        min_scale,
        aggregation_temporality,
    ):

        current_change = current_scale - min_scale

        for current_bucket_index, current_bucket in enumerate(
            current_buckets.counts
        ):

            if current_bucket == 0:
                continue

            # Not considering the case where len(previous_buckets) == 0. This
            # would not happen because self._previous_point is only assigned to
            # an ExponentialHistogramDataPoint object if self._count != 0.

            current_index = current_buckets.index_base + current_bucket_index
            if current_index > current_buckets.index_end:
                current_index -= len(current_buckets.counts)

            index = current_index >> current_change

            if index < previous_buckets.index_start:
                span = previous_buckets.index_end - index

                if span >= self._max_size:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Incorrect merge scale")

                if span >= len(previous_buckets.counts):
                    previous_buckets.grow(span + 1, self._max_size)

                previous_buckets.index_start = index

            if index > previous_buckets.index_end:
                span = index - previous_buckets.index_start

                if span >= self._max_size:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Incorrect merge scale")

                if span >= len(previous_buckets.counts):
                    previous_buckets.grow(span + 1, self._max_size)

                previous_buckets.index_end = index

            bucket_index = index - previous_buckets.index_base

            if bucket_index < 0:
                bucket_index += len(previous_buckets.counts)

            if aggregation_temporality is AggregationTemporality.DELTA:
                current_bucket = -current_bucket

            previous_buckets.increment_bucket(
                bucket_index, increment=current_bucket
            )


class Aggregation(ABC):
    """
    Base class for all aggregation types.
    """

    @abstractmethod
    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        """Creates an aggregation"""


class DefaultAggregation(Aggregation):
    """
    The default aggregation to be used in a `View`.

    This aggregation will create an actual aggregation depending on the
    instrument type, as specified next:

    ==================================================== ====================================
    Instrument                                           Aggregation
    ==================================================== ====================================
    `opentelemetry.sdk.metrics.Counter`                  `SumAggregation`
    `opentelemetry.sdk.metrics.UpDownCounter`            `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableCounter`        `SumAggregation`
    `opentelemetry.sdk.metrics.ObservableUpDownCounter`  `SumAggregation`
    `opentelemetry.sdk.metrics.Histogram`                `ExplicitBucketHistogramAggregation`
    `opentelemetry.sdk.metrics.ObservableGauge`          `LastValueAggregation`
    ==================================================== ====================================
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        # pylint: disable=too-many-return-statements
        if isinstance(instrument, Counter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_aggregation_temporality=(
                    AggregationTemporality.DELTA
                ),
                start_time_unix_nano=start_time_unix_nano,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_aggregation_temporality=(
                    AggregationTemporality.DELTA
                ),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_aggregation_temporality=(
                    AggregationTemporality.CUMULATIVE
                ),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_aggregation_temporality=(
                    AggregationTemporality.CUMULATIVE
                ),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, Histogram):
            return _ExplicitBucketHistogramAggregation(
                attributes,
                instrument_aggregation_temporality=(
                    AggregationTemporality.DELTA
                ),
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation(attributes)

        if isinstance(instrument, _Gauge):
            return _LastValueAggregation(attributes)

        # pylint: disable=broad-exception-raised
        raise Exception(f"Invalid instrument type {type(instrument)} found")


class ExponentialBucketHistogramAggregation(Aggregation):
    def __init__(
        self,
        max_size: int = 160,
        max_scale: int = 20,
    ):
        self._max_size = max_size
        self._max_scale = max_scale

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = (
                AggregationTemporality.CUMULATIVE
            )

        return _ExponentialBucketHistogramAggregation(
            attributes,
            instrument_aggregation_temporality,
            start_time_unix_nano,
            max_size=self._max_size,
            max_scale=self._max_scale,
        )


class ExplicitBucketHistogramAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - Count of Measurement values falling within explicit bucket boundaries.
    - Arithmetic sum of Measurement values in population. This SHOULD NOT be collected when used with instruments that record negative measurements, e.g. UpDownCounter or ObservableGauge.
    - Min (optional) Measurement value in population.
    - Max (optional) Measurement value in population.


    Args:
        boundaries: Array of increasing values representing explicit bucket boundary values.
        record_min_max: Whether to record min and max.
    """

    def __init__(
        self,
        boundaries: Sequence[float] = (
            0.0,
            5.0,
            10.0,
            25.0,
            50.0,
            75.0,
            100.0,
            250.0,
            500.0,
            750.0,
            1000.0,
            2500.0,
            5000.0,
            7500.0,
            10000.0,
        ),
        record_min_max: bool = True,
    ) -> None:
        self._boundaries = boundaries
        self._record_min_max = record_min_max

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = (
                AggregationTemporality.CUMULATIVE
            )

        return _ExplicitBucketHistogramAggregation(
            attributes,
            instrument_aggregation_temporality,
            start_time_unix_nano,
            self._boundaries,
            self._record_min_max,
        )


class SumAggregation(Aggregation):
    """This aggregation informs the SDK to collect:

    - The arithmetic sum of Measurement values.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:

        instrument_aggregation_temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            instrument_aggregation_temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            instrument_aggregation_temporality = (
                AggregationTemporality.CUMULATIVE
            )

        return _SumAggregation(
            attributes,
            isinstance(instrument, (Counter, ObservableCounter)),
            instrument_aggregation_temporality,
            start_time_unix_nano,
        )


class LastValueAggregation(Aggregation):
    """
    This aggregation informs the SDK to collect:

    - The last Measurement.
    - The timestamp of the last Measurement.
    """

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _LastValueAggregation(attributes)


class DropAggregation(Aggregation):
    """Using this aggregation will make all measurements be ignored."""

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _DropAggregation(attributes)
