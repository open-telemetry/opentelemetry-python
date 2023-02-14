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
)
from opentelemetry.sdk.metrics._internal.exponential_histogram.buckets import (
    Buckets,
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
    Gauge,
)
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
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _DropAggregation(_Aggregation):
    def aggregate(self, measurement: Measurement) -> None:
        pass

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        pass


class _SumAggregation(_Aggregation[Sum]):
    def __init__(
        self,
        attributes: Attributes,
        instrument_is_monotonic: bool,
        instrument_temporality: AggregationTemporality,
        start_time_unix_nano: int,
    ):
        super().__init__(attributes)

        self._start_time_unix_nano = start_time_unix_nano
        self._instrument_temporality = instrument_temporality
        self._instrument_is_monotonic = instrument_is_monotonic

        if self._instrument_temporality is AggregationTemporality.DELTA:
            self._value = 0
        else:
            self._value = None

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            if self._value is None:
                self._value = 0
            self._value = self._value + measurement.value

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[NumberDataPoint]:
        """
        Atomically return a point for the current value of the metric and
        reset the aggregation value.
        """
        if self._instrument_temporality is AggregationTemporality.DELTA:

            with self._lock:
                value = self._value
                start_time_unix_nano = self._start_time_unix_nano

                self._value = 0
                self._start_time_unix_nano = collection_start_nano

        else:

            with self._lock:
                if self._value is None:
                    return None
                value = self._value
                self._value = None
                start_time_unix_nano = self._start_time_unix_nano

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            value=value,
        )

        if self._previous_point is None or (
            self._instrument_temporality is aggregation_temporality
        ):
            # Output DELTA for a synchronous instrument
            # Output CUMULATIVE for an asynchronous instrument
            self._previous_point = current_point
            return current_point

        if aggregation_temporality is AggregationTemporality.DELTA:
            # Output temporality DELTA for an asynchronous instrument
            value = current_point.value - self._previous_point.value
            output_start_time_unix_nano = self._previous_point.time_unix_nano

        else:
            # Output CUMULATIVE for a synchronous instrument
            value = current_point.value + self._previous_point.value
            output_start_time_unix_nano = (
                self._previous_point.start_time_unix_nano
            )

        current_point = NumberDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=output_start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            value=value,
        )

        self._previous_point = current_point
        return current_point


class _LastValueAggregation(_Aggregation[Gauge]):
    def __init__(self, attributes: Attributes):
        super().__init__(attributes)
        self._value = None

    def aggregate(self, measurement: Measurement):
        with self._lock:
            self._value = measurement.value

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
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
            start_time_unix_nano=0,
            time_unix_nano=collection_start_nano,
            value=value,
        )


class _ExplicitBucketHistogramAggregation(_Aggregation[HistogramPoint]):
    def __init__(
        self,
        attributes: Attributes,
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
        self._bucket_counts = self._get_empty_bucket_counts()
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._record_min_max = record_min_max
        self._start_time_unix_nano = start_time_unix_nano
        # It is assumed that the "natural" aggregation temporality for a
        # Histogram instrument is DELTA, like the "natural" aggregation
        # temporality for a Counter is DELTA and the "natural" aggregation
        # temporality for an ObservableCounter is CUMULATIVE.
        self._instrument_temporality = AggregationTemporality.DELTA

    def _get_empty_bucket_counts(self) -> List[int]:
        return [0] * (len(self._boundaries) + 1)

    def aggregate(self, measurement: Measurement) -> None:

        value = measurement.value

        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        self._sum += value

        self._bucket_counts[bisect_left(self._boundaries, value)] += 1

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """
        with self._lock:
            if not any(self._bucket_counts):
                return None

            bucket_counts = self._bucket_counts
            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            min_ = self._min

            self._bucket_counts = self._get_empty_bucket_counts()
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._min = inf
            self._max = -inf

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=collection_start_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=self._boundaries,
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
            bucket_counts = [
                curr_count + prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]
        else:
            start_time_unix_nano = self._previous_point.time_unix_nano
            sum_ = current_point.sum - self._previous_point.sum
            bucket_counts = [
                curr_count - prev_count
                for curr_count, prev_count in zip(
                    current_point.bucket_counts,
                    self._previous_point.bucket_counts,
                )
            ]

        current_point = HistogramDataPoint(
            attributes=self._attributes,
            start_time_unix_nano=start_time_unix_nano,
            time_unix_nano=current_point.time_unix_nano,
            count=sum(bucket_counts),
            sum=sum_,
            bucket_counts=tuple(bucket_counts),
            explicit_bounds=current_point.explicit_bounds,
            min=min_,
            max=max_,
        )
        self._previous_point = current_point
        return current_point


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
        start_time_unix_nano: int,
        # This is the default maximum number of buckets per positive or
        # negative number range.  The value 160 is specified by OpenTelemetry.
        # See the derivation here:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exponential-bucket-histogram-aggregation)
        max_size: int = 160,
    ):
        super().__init__(attributes)
        # max_size is the maximum capacity of the positive and negative
        # buckets.
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

        self._max_size = max_size

        # _sum is the sum of all the values aggregated by this aggregator.
        self._sum = 0

        # _count is the count of all calls to aggregate.
        self._count = 0

        # _zero_count is the count of all the calls to aggregate when the value
        # to be aggregated is exactly 0.
        self._zero_count = 0

        # _min is the smallest value aggregated by this aggregator.
        self._min = inf

        # _max is the smallest value aggregated by this aggregator.
        self._max = -inf

        # _positive holds the positive values.
        self._positive = Buckets()

        # _negative holds the negative values by their absolute value.
        self._negative = Buckets()

        # _mapping corresponds to the current scale, is shared by both the
        # positive and negative buckets.
        self._mapping = LogarithmMapping(LogarithmMapping._max_scale)

        self._instrument_temporality = AggregationTemporality.DELTA
        self._start_time_unix_nano = start_time_unix_nano

    def aggregate(self, measurement: Measurement) -> None:
        # pylint: disable=too-many-branches,too-many-statements

        with self._lock:

            value = measurement.value

            # 0. Set the following attributes:
            # _min
            # _max
            # _count
            # _zero_count
            # _sum
            if value < self._min:
                self._min = value

            if value > self._max:
                self._max = value

            self._count += 1

            if value == 0:
                self._zero_count += 1
                # No need to do anything else if value is zero, just increment the
                # zero count.
                return

            self._sum += value

            # 1. Use the positive buckets for positive values and the negative
            # buckets for negative values.
            if value > 0:
                buckets = self._positive

            else:
                # Both exponential and logarithm mappings use only positive values
                # so the absolute value is used here.
                value = -value
                buckets = self._negative

            # 2. Compute the index for the value at the current scale.
            index = self._mapping.map_to_index(value)

            # 3. Determine if a change of scale is needed.
            is_rescaling_needed = False

            if len(buckets) == 0:
                buckets.index_start = index
                buckets.index_end = index
                buckets.index_base = index

            elif (
                index < buckets.index_start
                and (buckets.index_end - index) >= self._max_size
            ):
                is_rescaling_needed = True
                low = index
                high = buckets.index_end

            elif (
                index > buckets.index_end
                and (index - buckets.index_start) >= self._max_size
            ):
                is_rescaling_needed = True
                low = buckets.index_start
                high = index

            # 4. Rescale the mapping if needed.
            if is_rescaling_needed:

                change = 0

                while high - low >= self._max_size:
                    high = high >> 1
                    low = low >> 1

                    change += 1

                new_scale = self._mapping.scale - change

                self._positive.downscale(change)
                self._negative.downscale(change)

                if new_scale <= 0:
                    mapping = ExponentMapping(new_scale)
                else:
                    mapping = LogarithmMapping(new_scale)

                self._mapping = mapping

                index = self._mapping.map_to_index(value)

            # 5. If the index is outside
            # [buckets.index_start, buckets.index_end] readjust the buckets
            # boundaries or add more buckets.
            if index < buckets.index_start:
                span = buckets.index_end - index

                if span >= len(buckets.counts):
                    buckets.grow(span + 1, self._max_size)

                buckets.index_start = index

            elif index > buckets.index_end:
                span = index - buckets.index_start

                if span >= len(buckets.counts):
                    buckets.grow(span + 1, self._max_size)

                buckets.index_end = index

            # 6. Compute the index of the bucket to be incremented.
            bucket_index = index - buckets.index_base

            if bucket_index < 0:
                bucket_index += len(buckets.counts)

            # 7. Increment the bucket.
            buckets.increment_bucket(bucket_index)

    def collect(
        self,
        aggregation_temporality: AggregationTemporality,
        collection_start_nano: int,
    ) -> Optional[_DataPointVarT]:
        """
        Atomically return a point for the current value of the metric.
        """

        with self._lock:
            if self._count == 0:
                return None

            negative = self._negative
            positive = self._positive
            zero_count = self._zero_count
            count = self._count
            start_time_unix_nano = self._start_time_unix_nano
            sum_ = self._sum
            max_ = self._max
            if max_ == -inf:
                max_ = None
            min_ = self._min
            if min_ == inf:
                min_ = None

            if self._count == self._zero_count:
                scale = 0

            else:
                scale = self._mapping.scale

            self._negative = Buckets()
            self._positive = Buckets()
            self._start_time_unix_nano = collection_start_nano
            self._sum = 0
            self._count = 0
            self._zero_count = 0
            self._min = inf
            self._max = -inf

            current_point = ExponentialHistogramDataPoint(
                attributes=self._attributes,
                start_time_unix_nano=start_time_unix_nano,
                time_unix_nano=collection_start_nano,
                count=count,
                sum=sum_,
                scale=scale,
                zero_count=zero_count,
                positive=BucketsPoint(
                    offset=positive.offset,
                    bucket_counts=positive.counts,
                ),
                negative=BucketsPoint(
                    offset=negative.offset,
                    bucket_counts=negative.counts,
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

            previous_point = self._previous_point

            min_scale = min(previous_point.scale, current_point.scale)

            low_positive, high_positive = self._get_low_high(
                previous_point.positive, current_point.positive, min_scale
            )
            low_negative, high_negative = self._get_low_high(
                previous_point.negative, current_point.negative, min_scale
            )

            if aggregation_temporality is AggregationTemporality.CUMULATIVE:

                # attributes: always the same
                # start_time_unix_nano: defined below
                # time_unix_nano: defined in parameter above
                # count: treat as we do in explicit bucket histogram
                # sum: "
                # zero_count: "
                # scale: needs merging
                # positive: needs merging
                # negative: needs merging
                # min: treat as we do in explicit bucket histogram
                # max: treat as we do in explicit bucket histogram

                start_time_unix_nano = (
                    previous_point.start_time_unix_nano
                )
                sum_ = current_point.sum + previous_point.sum
                # Only update min/max on delta -> cumulative
                max_ = max(current_point.max, previous_point.max)
                min_ = min(current_point.min, previous_point.min)

                # Merging should be implemented here somehow
                negative_counts = [
                    curr_count + prev_count
                    for curr_count, prev_count in zip(
                        current_point.negative.bucket_counts,
                        previous_point.negative.bucket_counts,
                    )
                ]
                positive_counts = [
                    curr_count + prev_count
                    for curr_count, prev_count in zip(
                        current_point.positive.bucket_counts,
                        previous_point.positive.bucket_counts,
                    )
                ]
            else:
                start_time_unix_nano = previous_point.time_unix_nano
                sum_ = current_point.sum - previous_point.sum
                max_ = current_point.max
                min_ = current_point.min

                negative_counts = [
                    curr_count - prev_count
                    for curr_count, prev_count in zip(
                        current_point.negative.bucket_counts,
                        previous_point.negative.bucket_counts,
                    )
                ]
                positive_counts = [
                    curr_count - prev_count
                    for curr_count, prev_count in zip(
                        current_point.positive.bucket_counts,
                        previous_point.positive.bucket_counts,
                    )
                ]

            current_point = ExponentialHistogramDataPoint(
                attributes=self._attributes,
                start_time_unix_nano=start_time_unix_nano,
                time_unix_nano=current_point.time_unix_nano,
                count=count,
                sum=sum_,
                scale=scale,
                zero_count=zero_count,
                positive=BucketsPoint(
                    offset=positive.offset, bucket_counts=positive_counts
                ),
                negative=BucketsPoint(
                    offset=negative.offset, bucket_counts=negative_counts
                ),
                # FIXME: Find the right value for flags
                flags=0,
                min=min_,
                max=max_,
            )

            self._previous_point = current_point

            # FIXME this seems wrong, the values here should be updated
            # depending on the aggregation temporality (cumulative or delta)
            # the behavior here should be consistent with the sum and histogram
            # aggregations above.
            # Maybe what Srikanth says is that it does not make sense to return
            # a point with a certain bucket boundaries, then another with
            # different boundaries, that is maybe what Jmacd's merge methods
            # did.

            return current_point

    def _get_low_high_previous_current_buckets(
        self, previous_point_buckets, current_point_buckets, min_scale
    ):

        (
            previous_point_low,
            previous_point_high
        ) = self._get_low_high(
            previous_point_buckets,
            min_scale
        )
        (
            current_point_low,
            current_point_high
        ) = self._get_low_high(
            current_point_buckets,
            min_scale
        )

        if current_point_low > current_point_high:
            low = previous_point_low
            high = previous_point_high

        elif previous_point_low > previous_point_high:
            low = current_point_low
            high = current_point_high

        else:
            low = min(
                previous_point_low, current_point_low
            )
            high = min(
                previous_point_high, current_point_high
            )

        return low, high

    def _get_low_high(self, buckets, min_scale):
        if len(buckets) == 0:
            return 0, -1

        shift = self.scale - min_scale

        return buckets.index_start >> shift, buckets.index_end >> shift


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
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )
        if isinstance(instrument, UpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.DELTA,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=True,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, ObservableUpDownCounter):
            return _SumAggregation(
                attributes,
                instrument_is_monotonic=False,
                instrument_temporality=AggregationTemporality.CUMULATIVE,
                start_time_unix_nano=start_time_unix_nano,
            )

        if isinstance(instrument, Histogram):
            return _ExplicitBucketHistogramAggregation(
                attributes, start_time_unix_nano
            )

        if isinstance(instrument, ObservableGauge):
            return _LastValueAggregation(attributes)

        raise Exception(f"Invalid instrument type {type(instrument)} found")


class ExponentialBucketHistogramAggregation(Aggregation):
    def __init__(
        self,
        max_size: int = 160,
    ):

        self._max_size = max_size

    def _create_aggregation(
        self,
        instrument: Instrument,
        attributes: Attributes,
        start_time_unix_nano: int,
    ) -> _Aggregation:
        return _ExponentialBucketHistogramAggregation(
            attributes,
            start_time_unix_nano,
            max_size=self._max_size,
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
        return _ExplicitBucketHistogramAggregation(
            attributes,
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

        temporality = AggregationTemporality.UNSPECIFIED
        if isinstance(instrument, Synchronous):
            temporality = AggregationTemporality.DELTA
        elif isinstance(instrument, Asynchronous):
            temporality = AggregationTemporality.CUMULATIVE

        return _SumAggregation(
            attributes,
            isinstance(instrument, (Counter, ObservableCounter)),
            temporality,
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
