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

# pylint: disable=too-many-ancestors

import logging
from typing import Dict, Generator, Iterable, Optional, Union

from opentelemetry._metrics.instrument import CallbackT
from opentelemetry._metrics.instrument import Counter as APICounter
from opentelemetry._metrics.instrument import Histogram as APIHistogram
from opentelemetry._metrics.instrument import (
    ObservableCounter as APIObservableCounter,
)
from opentelemetry._metrics.instrument import (
    ObservableGauge as APIObservableGauge,
)
from opentelemetry._metrics.instrument import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry._metrics.instrument import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.measurement_consumer import MeasurementConsumer
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_logger = logging.getLogger(__name__)


class _Synchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        unit: str = "",
        description: str = "",
    ):
        self.name = name
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, unit=unit, description=description)


class _Asynchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        callbacks: Optional[Iterable[CallbackT]] = None,
        unit: str = "",
        description: str = "",
    ):
        self.name = name
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, callbacks, unit=unit, description=description)

        self._callbacks = []

        if callbacks is not None:

            for callback in callbacks:

                if isinstance(callback, Generator):

                    def inner(callback=callback) -> Iterable[Measurement]:
                        return next(callback)

                    self._callbacks.append(inner)
                else:
                    self._callbacks.append(callback)

    def callback(self) -> Iterable[Measurement]:
        for callback in self._callbacks:
            try:
                for api_measurement in callback():
                    yield Measurement(
                        api_measurement.value,
                        instrument=self,
                        attributes=api_measurement.attributes,
                    )
            except StopIteration:
                pass
            except Exception:  # pylint: disable=broad-except
                _logger.exception(
                    "Callback failed for instrument %s.", self.name
                )


class Counter(_Synchronous, APICounter):
    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        if amount < 0:
            _logger.warning(
                "Add amount must be non-negative on Counter %s.", self.name
            )
            return
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class UpDownCounter(_Synchronous, APIUpDownCounter):
    def add(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableCounter(_Asynchronous, APIObservableCounter):
    pass


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):
    pass


class Histogram(_Synchronous, APIHistogram):
    def record(
        self, amount: Union[int, float], attributes: Dict[str, str] = None
    ):
        if amount < 0:
            _logger.warning(
                "Record amount must be non-negative on Histogram %s.",
                self.name,
            )
            return
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableGauge(_Asynchronous, APIObservableGauge):
    pass
