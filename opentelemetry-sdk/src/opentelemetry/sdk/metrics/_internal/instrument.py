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

# pylint: disable=too-many-ancestors, unused-import

from logging import getLogger
from typing import Dict, Generator, Iterable, List, Optional, Union

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
from opentelemetry.metrics import CallbackT
from opentelemetry.metrics import Counter as APICounter
from opentelemetry.metrics import Histogram as APIHistogram
from opentelemetry.metrics import ObservableCounter as APIObservableCounter
from opentelemetry.metrics import ObservableGauge as APIObservableGauge
from opentelemetry.metrics import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry.metrics import UpDownCounter as APIUpDownCounter
from opentelemetry.metrics import _Gauge as APIGauge
from opentelemetry.metrics._internal.instrument import CallbackOptions
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_logger = getLogger(__name__)


_ERROR_MESSAGE = (
    "Expected ASCII string of maximum length 63 characters but got {}"
)


class _Synchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: "opentelemetry.sdk.metrics.MeasurementConsumer",  # type: ignore[name-defined] # <will add tracking issue num>
        unit: str = "",
        description: str = "",
    ):
        # pylint: disable=no-member
        result = self._check_name_unit_description(name, unit, description)  # type: ignore[attr-defined, misc] # <will add tracking issue num>

        if result["name"] is None:  # type: ignore[misc] # <will add tracking issue num>
            raise Exception(_ERROR_MESSAGE.format(name))

        if result["unit"] is None:  # type: ignore[misc] # <will add tracking issue num>
            raise Exception(_ERROR_MESSAGE.format(unit))

        name = result["name"]  # type: ignore[misc] # <will add tracking issue num>
        unit = result["unit"]  # type: ignore[misc] # <will add tracking issue num>
        description = result["description"]  # type: ignore[misc] # <will add tracking issue num>

        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, unit=unit, description=description)  # type: ignore[call-arg] # <will add tracking issue num>


class _Asynchronous:
    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: "opentelemetry.sdk.metrics.MeasurementConsumer",  # type: ignore[name-defined] # <will add tracking issue num>
        callbacks: Optional[Iterable[CallbackT]] = None,
        unit: str = "",
        description: str = "",
    ):
        # pylint: disable=no-member
        result = self._check_name_unit_description(name, unit, description)  # type: ignore[attr-defined, misc] # <will add tracking issue num>

        if result["name"] is None:  # type: ignore[misc] # <will add tracking issue num>
            raise Exception(_ERROR_MESSAGE.format(name))

        if result["unit"] is None:  # type: ignore[misc] # <will add tracking issue num>
            raise Exception(_ERROR_MESSAGE.format(unit))

        name = result["name"]  # type: ignore[misc] # <will add tracking issue num>
        unit = result["unit"]  # type: ignore[misc] # <will add tracking issue num>
        description = result["description"]  # type: ignore[misc] # <will add tracking issue num>

        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        super().__init__(name, callbacks, unit=unit, description=description)  # type: ignore[call-arg] # <will add tracking issue num>

        self._callbacks: List[CallbackT] = []

        if callbacks is not None:

            for callback in callbacks:

                if isinstance(callback, Generator):

                    # advance generator to it's first yield
                    next(callback)

                    def inner(  # type: ignore[no-untyped-def] # <will add tracking issue num>
                        options: CallbackOptions,
                        callback=callback,
                    ) -> Iterable[Measurement]:
                        try:
                            return callback.send(options)  # type: ignore[misc, no-any-return] # <will add tracking issue num>
                        except StopIteration:
                            return []

                    self._callbacks.append(inner)  # type: ignore[arg-type, misc] # <will add tracking issue num>
                else:
                    self._callbacks.append(callback)

    def callback(
        self, callback_options: CallbackOptions
    ) -> Iterable[Measurement]:
        for callback in self._callbacks:
            try:
                for api_measurement in callback(callback_options):  # type: ignore[misc, operator] # <will add tracking issue num>
                    yield Measurement(
                        api_measurement.value,  # type: ignore[misc] # <will add tracking issue num>
                        instrument=self,  # type: ignore[arg-type] # <will add tracking issue num>
                        attributes=api_measurement.attributes,  # type: ignore[misc] # <will add tracking issue num>
                    )
            except Exception:  # pylint: disable=broad-except
                _logger.exception(
                    "Callback failed for instrument %s.", self.name
                )


class Counter(_Synchronous, APICounter):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is Counter:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError("Counter must be instantiated via a meter.")
        return super().__new__(cls)

    def add(  # type: ignore[no-untyped-def, override] # <will add tracking issue num>
        self, amount: Union[int, float], attributes: Dict[str, str] = None  # type: ignore[assignment] # <will add tracking issue num>
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
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is UpDownCounter:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError("UpDownCounter must be instantiated via a meter.")
        return super().__new__(cls)

    def add(  # type: ignore[no-untyped-def, override] # <will add tracking issue num>
        self, amount: Union[int, float], attributes: Dict[str, str] = None  # type: ignore[assignment] # <will add tracking issue num>
    ):
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableCounter(_Asynchronous, APIObservableCounter):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is ObservableCounter:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError(
                "ObservableCounter must be instantiated via a meter."
            )
        return super().__new__(cls)


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is ObservableUpDownCounter:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError(
                "ObservableUpDownCounter must be instantiated via a meter."
            )
        return super().__new__(cls)


class Histogram(_Synchronous, APIHistogram):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is Histogram:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError("Histogram must be instantiated via a meter.")
        return super().__new__(cls)

    def record(  # type: ignore[no-untyped-def, override] # <will add tracking issue num>
        self, amount: Union[int, float], attributes: Dict[str, str] = None  # type: ignore[assignment] # <will add tracking issue num>
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


class Gauge(_Synchronous, APIGauge):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is Gauge:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError("Gauge must be instantiated via a meter.")
        return super().__new__(cls)

    def set(  # type: ignore[no-untyped-def, override] # <will add tracking issue num>
        self, amount: Union[int, float], attributes: Dict[str, str] = None  # type: ignore[assignment] # <will add tracking issue num>
    ):
        self._measurement_consumer.consume_measurement(
            Measurement(amount, self, attributes)
        )


class ObservableGauge(_Asynchronous, APIObservableGauge):
    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        if cls is ObservableGauge:  # type: ignore[misc] # <will add tracking issue num>
            raise TypeError(
                "ObservableGauge must be instantiated via a meter."
            )
        return super().__new__(cls)


# Below classes exist to prevent the direct instantiation
class _Counter(Counter):
    pass


class _UpDownCounter(UpDownCounter):
    pass


class _ObservableCounter(ObservableCounter):
    pass


class _ObservableUpDownCounter(ObservableUpDownCounter):
    pass


class _Histogram(Histogram):
    pass


class _Gauge(Gauge):
    pass


class _ObservableGauge(ObservableGauge):
    pass
