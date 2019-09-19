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

from typing import Dict, List, Tuple, Type, Union
from opentelemetry import metrics, trace as metrics_api, trace_api


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`.

    Args:
        name: The name of the meter.
    """
    def __init__(self, name: str = "") -> None:
        self.name = name

    def record_batch(
        self,
        label_tuples: Dict[str, str],
        record_tuples: List[Tuple[metrics_api.Metric, Union[float, int]]],
    ) -> None:
        pass


    def create_counter(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Union[Type[float], Type[int]],
        is_bidirectional: bool = False,
        label_keys: List[str] = None,
        span_context: trace_api.SpanContext = None,
    ) -> Union[metrics_api.FloatCounter, metrics_api.IntCounter]:
        """See `opentelemetry.metrics.Meter.create_counter`."""

class FloatCounter(metrics_api.FloatCounter):
    """See `opentelemetry.metrics.FloatCounter`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        is_bidirectional: bool = False,
        label_keys: List[str] = None,
        span_context: trace_api.SpanContext = None,
    ) -> None:
        self.name = name
        self.description = description
        self.unit = unit
        self.is_bidirectional = is_bidirectional
        self.label_keys = label_keys
        self.span_context = span_context
        self.handles = {}

    def get_handle(self,
                   label_values: List[str]) -> metrics_api.CounterHandle:
        """See `opentelemetry.metrics.FloatCounter.get_handle`."""
        handle = self.handles.get(label_values, CounterHandle(float, self.is_bidirectional))
        self.handles[label_values] = handle
        return handle


class CounterHandle(metrics_api.CounterHandle):

    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        is_bidirectional: bool) -> None:
        self.counter_data = 0
        self.type = value_type
        self.is_bidirectional = is_bidirectional

    def add(self, value: Union[float, int]) -> None:
        """See `opentelemetry.metrics.CounterHandle.add`."""
        if not self.is_bidirectional and value < 0:
            raise ValueError("Unidirectional counter cannot descend.")
        if not isinstance(value, self.value_type):
            raise ValueError("Invalid value passed for " + self.value_type)
        self.counter_data += value


meter = Meter()