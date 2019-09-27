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
from typing import Sequence, Tuple, Type

from opentelemetry import metrics as metrics_api

logger = logging.getLogger(__name__)


class BaseHandle:
    def __init__(
        self,
        value_type: Type[metrics_api.ValueT],
        enabled: bool,
        monotonic: bool,
    ):
        self.data = 0
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic

    def _validate_update(self, value: metrics_api.ValueT):
        if not self.enabled:
            return False
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return False
        return True


class CounterHandle(metrics_api.CounterHandle, BaseHandle):
    def update(self, value: metrics_api.ValueT) -> None:
        if self._validate_update(value):
            if self.monotonic and value < 0:
                logger.warning("Monotonic counter cannot descend.")
                return
            self.data += value

    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.CounterHandle._add`."""
        self.update(value)


class GaugeHandle(metrics_api.GaugeHandle, BaseHandle):
    def update(self, value: metrics_api.ValueT) -> None:
        if self._validate_update(value):
            if self.monotonic and value < self.data:
                logger.warning("Monotonic gauge cannot descend.")
                return
            self.data = value

    def set(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.GaugeHandle._set`."""
        self.update(value)


class MeasureHandle(metrics_api.MeasureHandle, BaseHandle):
    def update(self, value: metrics_api.ValueT) -> None:
        if self._validate_update(value):
            if self.monotonic and value < 0:
                logger.warning("Monotonic measure cannot accept negatives.")
                return
            # TODO: record

    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.MeasureHandle._record`."""
        self.update(value)


class Metric(metrics_api.Metric):
    """See `opentelemetry.metrics.Metric`."""

    HANDLE_TYPE = BaseHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.label_keys = label_keys
        self.enabled = enabled
        self.monotonic = monotonic
        self.handles = {}

    def get_handle(self, label_values: Sequence[str]) -> BaseHandle:
        """See `opentelemetry.metrics.Metric.get_handle`."""
        handle = self.handles.get(label_values)
        if not handle:
            handle = self.HANDLE_TYPE(
                self.value_type, self.enabled, self.monotonic
            )
        self.handles[label_values] = handle
        return handle


class Counter(Metric):
    """See `opentelemetry.metrics.Counter`.

    By default, counter values can only go up (monotonic). Negative inputs
    will be discarded for monotonic counter metrics. Counter metrics that
    have a monotonic option set to False allows negative inputs.
    """

    HANDLE_TYPE = CounterHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = True,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )


class Gauge(Metric):
    """See `opentelemetry.metrics.Gauge`.

    By default, gauge values can go both up and down (non-monotonic).
    Negative inputs will be discarded for monotonic gauge metrics.
    """

    HANDLE_TYPE = GaugeHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )


class Measure(Metric):
    """See `opentelemetry.metrics.Measure`.

    By default, measure metrics can accept both positive and negatives.
    Negative inputs will be discarded when monotonic is True.
    """

    HANDLE_TYPE = MeasureHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        label_keys: Sequence[str] = None,
        enabled: bool = False,
        monotonic: bool = False,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`."""

    def record_batch(
        self,
        label_values: Sequence[str],
        record_tuples: Sequence[Tuple[metrics_api.Metric, metrics_api.ValueT]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        for metric, value in record_tuples:
            metric.get_handle(label_values).update(value)

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        metric_type: Type[metrics_api.MetricT],
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ) -> metrics_api.MetricT:
        """See `opentelemetry.metrics.Meter.create_metric`."""
        return metric_type(
            name,
            description,
            unit,
            value_type,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )


meter = Meter()
