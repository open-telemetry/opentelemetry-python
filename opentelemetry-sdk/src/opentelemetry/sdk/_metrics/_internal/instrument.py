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

from abc import ABC
from typing import Iterable, Union

from opentelemetry import _metrics as metrics_api
from opentelemetry.sdk._metrics._internal.instrument_descriptor import (
    InstrumentDescriptor,
)
from opentelemetry.sdk._metrics._internal.measurement import (
    Measurement,
    SendMeasurementT,
)
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo


class SDKInstrumentBase(ABC):
    def __init__(
        self,
        name,
        unit,
        description,
        instrumentation_info: InstrumentationInfo,
    ):
        self._descriptor = InstrumentDescriptor(
            instrument_type=type(self),
            name=name,
            unit=unit,
            description=description,
            instrumentation_info=instrumentation_info,
        )

    @property
    def descriptor(self) -> InstrumentDescriptor:
        return self._descriptor


class SDKSynchronousInstrumentBase(SDKInstrumentBase):
    def __init__(
        self,
        name,
        unit,
        description,
        instrumentation_info: InstrumentationInfo,
        send_measurement: SendMeasurementT,
    ):
        super().__init__(name, unit, description, instrumentation_info)
        self._send_measurement = send_measurement


# Must be used with one of the concrete API instruments to provide self._callback
class SDKAsyncInstrumentBase(SDKInstrumentBase):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

    def callback(self) -> Iterable[Measurement]:
        for api_measurement in self._callback():
            yield Measurement(
                value=api_measurement.value,
                instrument_descriptor=self._descriptor,
                attributes=api_measurement.attributes,
            )


class Counter(SDKSynchronousInstrumentBase, metrics_api.Counter):
    def __init__(
        self,
        name,
        unit,
        description,
        instrumentation_info: InstrumentationInfo,
        send_measurement: SendMeasurementT,
    ):
        SDKSynchronousInstrumentBase.__init__(
            self,
            name,
            unit,
            description,
            instrumentation_info,
            send_measurement,
        )
        metrics_api.Counter.__init__(
            self, name, unit=unit, description=description
        )
        self._send_measurement = send_measurement

    def add(self, amount, attributes=None):
        self._send_measurement(
            Measurement(self._descriptor, amount, attributes)
        )


class ObservableCounter(SDKAsyncInstrumentBase, metrics_api.ObservableCounter):
    def __init__(
        self,
        name,
        unit,
        description,
        callback,
        instrumentation_info: InstrumentationInfo,
    ):
        SDKAsyncInstrumentBase.__init__(
            self,
            name,
            unit,
            description,
            instrumentation_info,
        )
        metrics_api.ObservableCounter.__init__(
            self,
            name,
            callback,
            unit=unit,
            description=description,
        )


class ObservableGauge(SDKAsyncInstrumentBase, metrics_api.ObservableGauge):
    def __init__(
        self,
        name,
        unit,
        description,
        callback,
        instrumentation_info: InstrumentationInfo,
    ):
        SDKAsyncInstrumentBase.__init__(
            self,
            name,
            unit,
            description,
            instrumentation_info,
        )
        metrics_api.ObservableGauge.__init__(
            self,
            name,
            callback,
            unit=unit,
            description=description,
        )
