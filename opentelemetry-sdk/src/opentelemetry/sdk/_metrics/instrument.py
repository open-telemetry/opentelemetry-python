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

# pylint: disable=function-redefined
# pylint: disable=dangerous-default-value
# Classes in this module use dictionaries as default arguments. This is
# considered dangerous by pylint because the default dictionary is shared by
# all instances. Implementations of these classes must not make any change to
# this default dictionary in __init__.

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
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo


class _Instrument:
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        self._instrumentation_info = instrumentation_info
        super().__init__(name, unit=unit, description=description)


class Counter(_Instrument, APICounter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )

    def add(self, amount, attributes=None):
        # FIXME check that the amount is non negative
        pass


class UpDownCounter(_Instrument, APIUpDownCounter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )

    def add(self, amount, attributes=None):
        pass


class ObservableCounter(_Instrument, APIObservableCounter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )


class ObservableUpDownCounter(_Instrument, APIObservableUpDownCounter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )


class Histogram(_Instrument, APIHistogram):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )

    def record(self, amount, attributes=None):
        pass


class ObservableGauge(_Instrument, APIObservableGauge):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        name: str,
        unit: str = "",
        description: str = "",
    ):
        super().__init__(
            instrumentation_info,
            name,
            unit=unit,
            description=description,
        )
