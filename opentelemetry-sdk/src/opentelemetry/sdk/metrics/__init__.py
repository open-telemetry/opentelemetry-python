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
from typing import Tuple, Type, Union

from opentelemetry import metrics as metrics_api

logger = logging.getLogger(__name__)


class Metric(metrics_api.Metric):
    """See `opentelemetry.metrics.Metric`."""

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: metrics_api.ValueType,
        label_keys: Tuple[str, ...] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        self.name = name
        self.description = description
        self.unit = (unit,)
        self.value_type = value_type
        self.label_keys = label_keys
        self.enabled = enabled
        self.monotonic = monotonic
        self.handles = {}

    def get_handle(
        self, label_values: Tuple[str, ...]
    ) -> metrics_api.MetricHandle:
        """See `opentelemetry.metrics.Metric.get_handle`."""
        pass  # pylint: disable=unnecessary-pass

    def remove_handle(self, label_values: Tuple[str, ...]) -> None:
        """See `opentelemetry.metrics.Metric.remove_handle`."""
        self.handles.pop(label_values, None)

    def clear(self) -> None:
        """See `opentelemetry.metrics.Metric.clear`."""
        self.handles.clear()


class Counter(Metric):
    """See `opentelemetry.metrics.Counter`.

    By default, counter values can only go up (monotonic). Negative inputs
    will be discarded for monotonic counter metrics. Counter metrics that
    have a monotonic option set to False allows negative inputs.
    """

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: metrics_api.ValueType,
        label_keys: Tuple[str, ...] = None,
        enabled: bool = True,
        monotonic: bool = True,
    ):
        super(Counter, self).__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def get_handle(
        self, label_values: Tuple[str, ...]
    ) -> metrics_api.CounterHandle:
        """See `opentelemetry.metrics.FloatCounter.get_handle`."""
        handle = self.handles.get(
            label_values,
            CounterHandle(self.value_type, self.enabled, self.monotonic),
        )
        self.handles[label_values] = handle
        return handle


class Gauge(Metric):
    """See `opentelemetry.metrics.Gauge`.

    By default, gauge values can go both up and down (non-monotonic).
    Negative inputs will be discarded for monotonic gauge metrics.
    """

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: metrics_api.ValueType,
        label_keys: Tuple[str, ...] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        super(Gauge, self).__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def get_handle(
        self, label_values: Tuple[str, ...]
    ) -> metrics_api.GaugeHandle:
        """See `opentelemetry.metrics.Gauge.get_handle`."""
        handle = self.handles.get(
            label_values,
            GaugeHandle(self.value_type, self.enabled, self.monotonic),
        )
        self.handles[label_values] = handle
        return handle


class Measure(Metric):
    """See `opentelemetry.metrics.Measure`.

    By default, measure metrics can accept both positive and negatives.
    Negative inputs will be discarded when monotonic is True.
    """

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: metrics_api.ValueType,
        label_keys: Tuple[str, ...] = None,
        enabled: bool = False,
        monotonic: bool = False,
    ):
        super(Measure, self).__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def get_handle(
        self, label_values: Tuple[str, ...]
    ) -> metrics_api.MeasureHandle:
        """See `opentelemetry.metrics.Measure.get_handle`."""
        handle = self.handles.get(
            label_values,
            MeasureHandle(self.value_type, self.enabled, self.monotonic),
        )
        self.handles[label_values] = handle
        return handle


class CounterHandle(metrics_api.CounterHandle):
    def __init__(
        self, value_type: metrics_api.ValueType, enabled: bool, monotonic: bool
    ):
        self.data = 0
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic

    def update(self, value: metrics_api.ValueType) -> None:
        if not self.enabled:
            return
        if not self.monotonic and value < 0:
            logger.warning("Monotonic counter cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return
        self.data += value

    def add(self, value: metrics_api.ValueType) -> None:
        """See `opentelemetry.metrics.CounterHandle._add`."""
        self.update(value)


class GaugeHandle(metrics_api.GaugeHandle):
    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        enabled: bool,
        monotonic: bool,
    ):
        self.data = 0
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic

    def update(self, value: metrics_api.ValueType) -> None:
        if not self.enabled:
            return
        if self.monotonic and value < 0:
            logger.warning("Monotonic gauge cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s", self.value_type.__name__
            )
            return
        self.data = value

    def set(self, value: metrics_api.ValueType) -> None:
        """See `opentelemetry.metrics.GaugeHandle._set`."""
        self.update(value)


class MeasureHandle(metrics_api.MeasureHandle):
    def __init__(
        self,
        value_type: Union[Type[float], Type[int]],
        enabled: bool,
        monotonic: bool,
    ):
        self.data = 0
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic

    def update(self, value: metrics_api.ValueType) -> None:
        if not self.enabled:
            return
        if self.monotonic and value < 0:
            logger.warning("Monotonic measure cannot descend.")
            return
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s", self.value_type.__name__
            )
            return
        # TODO: record

    def record(self, value: metrics_api.ValueType) -> None:
        """See `opentelemetry.metrics.MeasureHandle._record`."""
        self.update(value)


METRIC_KIND_MAP = {
    metrics_api.MetricKind.COUNTER: Counter,
    metrics_api.MetricKind.GAUGE: Gauge,
    metrics_api.MetricKind.MEASURE: Measure,
}


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`."""

    def record_batch(
        self,
        label_values: Tuple[str, ...],
        record_tuples: Tuple[Tuple[metrics_api.Metric, metrics_api.ValueType]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        for metric, value in record_tuples:
            metric.get_handle(label_values).update(value)

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: metrics_api.ValueType,
        metric_kind: metrics_api.MetricKind,
        label_keys: Tuple[str, ...] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ) -> "Metric":
        """See `opentelemetry.metrics.Meter.create_metric`."""
        return METRIC_KIND_MAP[metric_kind](
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )


meter = Meter()
