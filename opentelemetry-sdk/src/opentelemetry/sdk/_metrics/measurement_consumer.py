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
from threading import Lock
from typing import TYPE_CHECKING, Iterable, List, Mapping

from opentelemetry.sdk._metrics.aggregation import AggregationTemporality
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.metric_reader_storage import (
    MetricReaderStorage,
)
from opentelemetry.sdk._metrics.point import Metric
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration

if TYPE_CHECKING:
    from opentelemetry.sdk._metrics.instrument import _Asynchronous


class MeasurementConsumer(ABC):
    @abstractmethod
    def consume_measurement(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def register_asynchronous_instrument(self, instrument: "_Asynchronous"):
        pass

    @abstractmethod
    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        pass


class SynchronousMeasurementConsumer(MeasurementConsumer):
    def __init__(self, sdk_config: SdkConfiguration) -> None:
        self._lock = Lock()
        self._sdk_config = sdk_config
        # should never be mutated
        self._reader_storages: Mapping[MetricReader, MetricReaderStorage] = {
            reader: MetricReaderStorage(sdk_config)
            for reader in sdk_config.metric_readers
        }
        self._async_instruments: List["_Asynchronous"] = []

    def consume_measurement(self, measurement: Measurement) -> None:
        for reader_storage in self._reader_storages.values():
            reader_storage.consume_measurement(measurement)

    def register_asynchronous_instrument(
        self, instrument: "_Asynchronous"
    ) -> None:
        with self._lock:
            self._async_instruments.append(instrument)

    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        with self._lock:
            metric_reader_storage = self._reader_storages[metric_reader]
            for async_instrument in self._async_instruments:
                for measurement in async_instrument.callback():
                    metric_reader_storage.consume_measurement(measurement)
        return self._reader_storages[metric_reader].collect(temporality)
