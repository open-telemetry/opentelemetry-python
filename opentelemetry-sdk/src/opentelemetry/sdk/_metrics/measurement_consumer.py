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
from typing import Iterable

from opentelemetry.sdk._metrics.aggregation import AggregationTemporality
from opentelemetry.sdk._metrics.data import Metric
from opentelemetry.sdk._metrics.instrument import _Asynchronous
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.metric_reader import MetricReader


class MeasurementConsumer(ABC):
    @abstractmethod
    def consume_measurement(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def register_asynchronous_instrument(self, instrument: _Asynchronous):
        pass

    @abstractmethod
    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        pass


class SynchronousMeasurementConsumer(MeasurementConsumer):
    def consume_measurement(self, measurement: Measurement) -> None:
        pass

    def register_asynchronous_instrument(
        self, instrument: _Asynchronous
    ) -> None:
        pass

    def collect(
        self, metric_reader: MetricReader, temporality: AggregationTemporality
    ) -> Iterable[Metric]:
        pass
