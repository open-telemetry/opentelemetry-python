# Copyright 2019, OpenTelemetry Authors
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

from typing import List, Tuple, Type, Union
from opentelemetry import metrics as metrics_api

logger = logging.getLogger(__name__)


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`.

    Args:
        name: The name of the meter.
    """
    def __init__(self, name: str = "") -> None:
        self.name = name

    def record_batch(
        self,
        label_values: Tuple[str],
        record_tuples: List[Tuple[metrics_api.Metric, Union[float, int]]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        for pair in record_tuples:
            handle = pair[0].get_handle(label_values)
            handle.update(pair[1])


    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: List[str] = None,
        disabled: bool = False,
        non_monotonic: bool = False,
    ) -> Union[metrics_api.FloatCounter, metrics_api.IntCounter]:
        """See `opentelemetry.metrics.Meter.create_counter`."""
        counter_class = FloatCounter if value_type == float else IntCounter
        return counter_class(
            name,
            description,
            unit,
            label_keys=label_keys,
            disabled=disabled,
            non_monotonic=non_monotonic)

    
    def create_gauge(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: List[str] = None,
        disabled: bool = False,
        is_monotonic: bool = False,
    ) -> Union[metrics_api.FloatGauge, metrics_api.IntGauge]:
        """See `opentelemetry.metrics.Meter.create_gauge`."""
        gauge_class = FloatGauge if value_type == float else IntGauge
        return gauge_class(
            name,
            description,
            unit,
            label_keys=label_keys,
            disabled=disabled,
            is_monotonic=is_monotonic)

    def create_measure(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        label_keys: List[str] = None,
        disabled: bool = False,
        non_negative: bool = False,
    ) -> Union[metrics_api.FloatMeasure, metrics_api.IntMeasure]:
        """See `opentelemetry.metrics.Meter.create_measure`."""
        measure_class = FloatMeasure if value_type == float else IntMeasure
        return measure_class(
            name,
            description,
            unit,
            label_keys=label_keys,
            disabled=disabled,
            non_negative=non_negative)
        

class FloatCounter(metrics_api.FloatCounter):
    """See `opentelemetry.metrics.FloatCounter`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        non_monotonic: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.non_monotonic = non_monotonic
        self.handles = {}

    def get_handle(self,
                   label_values: Tuple[str]) -> metrics_api.CounterHandle:
        """See `opentelemetry.metrics.FloatCounter.get_handle`."""
        handle = self.handles.get(
            label_values,
            CounterHandle(float, self.disabled, self.non_monotonic))
        self.handles[label_values] = handle
        return handle


class IntCounter(metrics_api.IntCounter):
    """See `opentelemetry.metrics.IntCounter`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        non_monotonic: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.non_monotonic = non_monotonic
        self.handles = {}

    def get_handle(self,
                   label_values: List[str]) -> metrics_api.GaugeHandle:
        """See `opentelemetry.metrics.IntCounter.get_handle`."""
        handle = self.handles.get(
            label_values,
            GaugeHandle(int, self.disabled, self.non_monotonic))
        self.handles[label_values] = handle
        return handle


class FloatGauge(metrics_api.FloatGauge):
    """See `opentelemetry.metrics.FloatGauge`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        is_monotonic: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.is_monotonic = is_monotonic
        self.handles = {}

    def get_handle(self,
                   label_values: Tuple[str]) -> metrics_api.GaugeHandle:
        """See `opentelemetry.metrics.FloatGauge.get_handle`."""
        handle = self.handles.get(
            label_values,
            GaugeHandle(float, self.disabled, self.is_monotonic))
        self.handles[label_values] = handle
        return handle


class IntGauge(metrics_api.IntGauge):
    """See `opentelemetry.metrics.IntGauge`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        is_monotonic: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.is_monotonic = is_monotonic
        self.handles = {}

    def get_handle(self,
                   label_values: List[str]) -> metrics_api.GaugeHandle:
        """See `opentelemetry.metrics.IntGauge.get_handle`."""
        handle = self.handles.get(
            label_values,
            GaugeHandle(int, self.disabled, self.is_monotonic))
        self.handles[label_values] = handle
        return handle


class FloatMeasure(metrics_api.FloatMeasure):
    """See `opentelemetry.metrics.FloatMeasure`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        non_negative: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.non_negative = non_negative
        self.handles = {}

    def get_handle(self,
                   label_values: Tuple[str]) -> metrics_api.MeasureHandle:
        """See `opentelemetry.metrics.FloatMeasure.get_handle`."""
        handle = self.handles.get(
            label_values,
            MeasureHandle(float, self.disabled, self.non_negative))
        self.handles[label_values] = handle
        return handle


class IntMeasure(metrics_api.IntMeasure):
    """See `opentelemetry.metrics.IntMeasure`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        label_keys: List[str] = None,
        disabled: bool = False,
        non_negative: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.label_keys = label_keys
        self.disabled = disabled
        self.non_negative = non_negative
        self.handles = {}

    def get_handle(self,
                   label_values: List[str]) -> metrics_api.MeasureHandle:
        """See `opentelemetry.metrics.IntMeasure.get_handle`."""
        handle = self.handles.get(
            label_values,
            MeasureHandle(int, self.disabled, self.non_negative))
        self.handles[label_values] = handle
        return handle


class CounterHandle(metrics_api.CounterHandle):

    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        disabled: bool,
        non_monotonic: bool) -> None:
        self.data = 0
        self.value_type = value_type
        self.disabled = disabled
        self.non_monotonic = non_monotonic

    def update(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.CounterHandle.update`."""
        self._add(value)

    def _add(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.CounterHandle._add`."""
        if self.disabled:
            logger.warning("Counter metric is disabled.")
            return
        if not self.non_monotonic and value < 0:
            logger.warning("Monotonic counter cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning("Invalid value passed for %s", self.value_type.__name__)
            return
        self.data += value


class GaugeHandle(metrics_api.GaugeHandle):

    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        disabled: bool,
        is_monotonic: bool) -> None:
        self.data = 0
        self.value_type = value_type
        self.disabled = disabled
        self.is_monotonic = is_monotonic

    def update(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.GaugeHandle.update`."""
        self._set(value)

    def _set(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.GaugeHandle._set`."""
        if self.disabled:
            logger.warning("Gauge metric is disabled.")
            return
        if self.is_monotonic and value < 0:
            logger.warning("Monotonic gauge cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning("Invalid value passed for %s", self.value_type.__name__)
            return
        self.data = value


class MeasureHandle(metrics_api.MeasureHandle):

    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        disabled: bool,
        non_negative: bool) -> None:
        self.data = 0
        self.value_type = value_type
        self.disabled = disabled
        self.non_negative = non_negative

    def update(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.MeasureHandle.update`."""
        self._record(value)

    def _record(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.MeasureHandle._record`."""
        if self.disabled:
            logger.warning("Measure metric is disabled.")
            return
        if self.non_negative and value < 0:
            logger.warning("Non-negative measure cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning("Invalid value passed for %s", self.value_type.__name__)
            return
        # TODO: record


meter = Meter()