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


import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from threading import Lock, RLock
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
)

from opentelemetry.sdk._metrics._internal.instrument import (
    Counter,
    ObservableCounter,
    ObservableGauge,
    SDKAsyncInstrumentBase,
)
from opentelemetry.sdk._metrics._internal.instrument_descriptor import (
    InstrumentDescriptor,
)
from opentelemetry.sdk._metrics._internal.measurement import (
    Measurement,
    ValueT,
)
from opentelemetry.sdk._metrics._internal.metric_reader import MetricReader
from opentelemetry.sdk._metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    PointT,
    Sum,
)
from opentelemetry.sdk._metrics.view import View, ViewSelector
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util import get_dict_as_key
from opentelemetry.util._time import _time_ns
from opentelemetry.util.types import Attributes, AttributesAsKey

_PointVarT = TypeVar("_PointVarT", bound=PointT)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SdkConfiguration:
    resource: Resource
    views: Sequence[View]
    metric_readers: Sequence[MetricReader]


# TODO: this is not the greatest name
class MeasurementProcessor(ABC):
    @abstractmethod
    def consume_measurement(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def register_async_instrument(
        self, instrument: SDKAsyncInstrumentBase
    ) -> None:
        pass

    @abstractmethod
    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        pass


class DefaultMetricProcessor(MeasurementProcessor):
    def __init__(self, sdk_config: SdkConfiguration) -> None:
        self._lock = Lock()
        # should never be mutated
        self._reader_to_state: Mapping[MetricReader, MetricReaderState] = {
            reader: MetricReaderState(sdk_config)
            for reader in sdk_config.metric_readers
        }
        self._async_instruments: List[SDKAsyncInstrumentBase] = []

    def consume_measurement(self, measurement: Measurement) -> None:
        for reader_state in self._reader_to_state.values():
            reader_state.consume_measurement(measurement)

    def register_async_instrument(
        self, instrument: SDKAsyncInstrumentBase
    ) -> None:
        with self._lock:
            self._async_instruments.append(instrument)

    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        with self._lock:
            for async_instrument in self._async_instruments:
                for measurement in async_instrument.callback():
                    self.consume_measurement(measurement)
        return self._reader_to_state[metric_reader].collect(temporality)


class MetricReaderState:
    """The SDK's state for a given reader"""

    def __init__(self, sdk_config: SdkConfiguration) -> None:
        self._lock = RLock()
        self._sdk_config = sdk_config
        self._view_index: Dict[InstrumentDescriptor, List["ViewStorage"]] = {}

    def _get_or_init_view_data(
        self, descriptor: InstrumentDescriptor
    ) -> List["ViewStorage"]:
        # Optimistically get the relevant views for the given instrument. Once set for a given
        # descriptor, the mapping will never change
        if descriptor in self._view_index:
            return self._view_index[descriptor]

        with self._lock:
            # double check if it was set before we held the lock
            if descriptor in self._view_index:
                return self._view_index[descriptor]

            # not present, hold the lock and add a new mapping
            view_datas = []
            for view in self._sdk_config.views:
                # TODO: implement all the selection matching
                if view.selector.instrument_name == descriptor.name:
                    # Note: if a view matches multiple instruments, this will create a separate
                    # ViewStorage per instrument. If the user's View configuration includes a
                    # name, this will cause multiple writers for the same stream.
                    view_datas.append(
                        ViewStorage(view, descriptor, self._sdk_config)
                    )

            # if no view targeted the instrument, use the default
            if not view_datas:
                view_datas.append(
                    ViewStorage(
                        default_view(descriptor), descriptor, self._sdk_config
                    )
                )
            self._view_index[descriptor] = view_datas
            return view_datas

    def consume_measurement(self, measurement: Measurement) -> None:
        view_datas = self._get_or_init_view_data(
            measurement.instrument_descriptor
        )
        for data in view_datas:
            data.consume_measurement(measurement)

    def collect(self, temporality: AggregationTemporality) -> Iterable[Metric]:
        # use a list instead of yielding to prevent a slow reader from holding SDK locks
        metrics: List[Metric] = []

        # While holding the lock, new ViewStorage can't be added from another thread (so we are
        # sure we collect all existing view). However, instruments can still send measurements
        # that will make it into the individual aggregations; collection will acquire those
        # locks iteratively to keep locking as fine-grained as possible. One side effect is
        # that end times will be slightly skewed among the metric streams produced by the SDK.
        with self._lock:
            for view_datas in self._view_index.values():
                for view_data in view_datas:
                    metrics.extend(view_data.collect(temporality))

        return metrics


def default_view(descriptor: InstrumentDescriptor) -> View:
    return View(selector=ViewSelector(instrument_name=descriptor.name))


class ViewStorage:
    def __init__(
        self,
        view: View,
        instrument_descriptor: InstrumentDescriptor,
        sdk_config: SdkConfiguration,
    ) -> None:
        self._lock = Lock()
        self._view = view
        self._instrument_descriptor = instrument_descriptor
        self._sdk_config = sdk_config
        self._attributes_to_aggregation: Dict[
            AttributesAsKey, Aggregation
        ] = {}
        # Maps attributes onto the cumulative value from the previous collection
        self._attributes_to_last_value: Dict[AttributesAsKey, PointT] = {}

    def consume_measurement(self, measurement: Measurement) -> None:
        attr_key = self._attribute_key(measurement.attributes)
        # TODO: do we need this lock? if we flush old entries then certainly
        with self._lock:
            agg = self._attributes_to_aggregation.setdefault(
                attr_key,
                Aggregation.create(self._view, self._instrument_descriptor),
            )
        agg.aggregate(measurement)

    def collect(self, temporality: AggregationTemporality) -> Iterable[Metric]:
        with self._lock:
            for attributes_key, agg in self._attributes_to_aggregation.items():
                last_value_cumulative = self._attributes_to_last_value.get(
                    attributes_key
                )
                point = agg.make_point_and_reset()
                point_in_temporality = convert_temporality(
                    last_value_cumulative, point, temporality
                )
                # Update with the next collection
                self._attributes_to_last_value[
                    attributes_key
                ] = convert_temporality(
                    last_value_cumulative,
                    point,
                    AggregationTemporality.CUMULATIVE,
                )

                if point is not None:
                    yield Metric(
                        attributes=dict(attributes_key),
                        description=self._instrument_descriptor.description,
                        instrumentation_info=self._instrument_descriptor.instrumentation_info,
                        name=self._view.name
                        or self._instrument_descriptor.name,
                        resource=self._sdk_config.resource,
                        unit=self._instrument_descriptor.unit,
                        point=point_in_temporality,
                    )

    def _attribute_key(self, attributes: Attributes) -> AttributesAsKey:
        # TODO: remove keys that are not recognized by the view
        if attributes is None:
            return tuple()
        return get_dict_as_key(attributes)


class Aggregation(ABC, Generic[_PointVarT]):
    """Represents a running aggregation"""

    def __init__(self) -> None:
        self._lock = Lock()

    @abstractmethod
    def aggregate(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def make_point_and_reset(self) -> Optional[_PointVarT]:
        """Return a (delta) point for the current value of the metric and reset the internal
        state for a new delta interval.
        """
        pass

    @staticmethod
    def create(
        view: View, descriptor: InstrumentDescriptor
    ) -> "Aggregation[PointT]":
        # TODO: if view has a custom aggregation, use that
        if descriptor.instrument_type is Counter:
            return SumAggregation()
        elif descriptor.instrument_type is ObservableCounter:
            return AsyncSumAggregation()
        elif descriptor.instrument_type is ObservableGauge:
            return LastValueAggregation()


class SumAggregation(Aggregation[Sum]):
    def __init__(self) -> None:
        super().__init__()
        self._value = 0
        self._start_time_unix_nano = _time_ns()

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            self._value += measurement.value

    def make_point_and_reset(self) -> Sum:
        now = _time_ns()
        with self._lock:
            point_value = self._value
            point_start_time = self._start_time_unix_nano
            self._value = 0
            self._start_time_unix_nano = now + 1

        return Sum(
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=True,
            start_time_unix_nano=point_start_time,
            time_unix_nano=now,
            value=point_value,
        )


class AsyncSumAggregation(Aggregation[Sum]):
    def __init__(self) -> None:
        super().__init__()
        self._value: Optional[ValueT] = None
        self._start_time_unix_nano = _time_ns()

    def aggregate(self, measurement: Measurement) -> None:
        # For async instruments, the measurement is the Sum's value so no addition needed.
        with self._lock:
            self._value = measurement.value

    def make_point_and_reset(self) -> Optional[Sum]:
        with self._lock:
            value = self._value
            self._value = None

        if value is None:
            return None
        return Sum(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
            start_time_unix_nano=self._start_time_unix_nano,
            time_unix_nano=_time_ns(),
            value=value,
        )


class LastValueAggregation(Aggregation[Gauge]):
    def __init__(self) -> None:
        super().__init__()
        self._value: Optional[ValueT] = None

    def aggregate(self, measurement: Measurement) -> None:
        with self._lock:
            self._value = measurement.value

    def make_point_and_reset(self) -> Optional[Gauge]:
        with self._lock:
            value = self._value
            self._value = None

        if value is None:
            return None
        return Gauge(
            value=value,
            time_unix_nano=_time_ns(),
        )


def convert_temporality(
    prev: Optional[_PointVarT],
    cur: _PointVarT,
    temporality: AggregationTemporality,
) -> _PointVarT:
    point_type = type(cur)
    if prev is not None and type(prev) is not point_type:
        _logger.warning(
            "convert_temporality() called with mismatched point types: %s and %s",
            type(prev),
            type(cur),
        )
        return cur

    if point_type is Sum:
        if prev is None:
            return replace(cur, aggregation_temporality=temporality)

        is_monotonic = prev.is_monotonic and cur.is_monotonic

        if temporality is AggregationTemporality.DELTA:
            # output delta, input delta
            if cur.aggregation_temporality is AggregationTemporality.DELTA:
                # synchronous delta case
                return cur
            # output delta, input cumulative
            return Sum(
                aggregation_temporality=temporality,
                is_monotonic=is_monotonic,
                start_time_unix_nano=prev.time_unix_nano,
                time_unix_nano=cur.time_unix_nano,
                value=cur.value - prev.value,
            )
        else:
            # output cumulative, input delta
            if cur.aggregation_temporality is AggregationTemporality.DELTA:
                return Sum(
                    aggregation_temporality=temporality,
                    is_monotonic=is_monotonic,
                    start_time_unix_nano=prev.start_time_unix_nano,
                    time_unix_nano=cur.time_unix_nano,
                    value=cur.value + prev.value,
                )
            # output cumulative, input cumulative
            return cur
    elif point_type is Gauge:
        # temporality is N/A, just return
        return cur
