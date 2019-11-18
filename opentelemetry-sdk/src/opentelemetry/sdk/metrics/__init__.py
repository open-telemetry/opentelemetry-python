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
from collections import OrderedDict
from typing import Dict, Sequence, Tuple, Type

from opentelemetry import metrics as metrics_api
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


# pylint: disable=redefined-outer-name
class LabelSet(metrics_api.LabelSet):
    """See `opentelemetry.metrics.LabelSet."""

    def __init__(
        self,
        meter: "Meter" = None,
        labels: Dict[str, str] = None,
        encoded: str = "",
    ):
        self.meter = meter
        self.labels = labels
        self.encoded = encoded


class BaseHandle:
    def __init__(
        self,
        value_type: Type[metrics_api.ValueT],
        enabled: bool,
        monotonic: bool,
    ):
        self.data = value_type()
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic
        self.last_update_timestamp = time_ns()

    def _validate_update(self, value: metrics_api.ValueT) -> bool:
        if not self.enabled:
            return False
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return False
        return True

    def __repr__(self):
        return '{}(data="{}", last_update_timestamp={})'.format(
            type(self).__name__, self.data, self.last_update_timestamp
        )


class CounterHandle(metrics_api.CounterHandle, BaseHandle):
    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.CounterHandle.add`."""
        if self._validate_update(value):
            if self.monotonic and value < 0:
                logger.warning("Monotonic counter cannot descend.")
                return
            self.last_update_timestamp = time_ns()
            self.data += value


class GaugeHandle(metrics_api.GaugeHandle, BaseHandle):
    def set(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.GaugeHandle.set`."""
        if self._validate_update(value):
            if self.monotonic and value < self.data:
                logger.warning("Monotonic gauge cannot descend.")
                return
            self.last_update_timestamp = time_ns()
            self.data = value


class MeasureHandle(metrics_api.MeasureHandle, BaseHandle):
    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.MeasureHandle.record`."""
        if self._validate_update(value):
            if self.monotonic and value < 0:
                logger.warning("Monotonic measure cannot accept negatives.")
                return
            self.last_update_timestamp = time_ns()
            # TODO: record


class Metric(metrics_api.Metric):
    """See `opentelemetry.metrics.Metric`."""

    HANDLE_TYPE = BaseHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.label_keys = label_keys
        self.enabled = enabled
        self.monotonic = monotonic
        self.handles = {}

    def get_handle(self, label_set: LabelSet) -> BaseHandle:
        """See `opentelemetry.metrics.Metric.get_handle`."""
        lable_set_for = self._label_set_for(label_set)
        handle = self.handles.get(lable_set_for.encoded)
        if not handle:
            handle = self.HANDLE_TYPE(
                self.value_type, self.enabled, self.monotonic
            )
        self.handles[lable_set_for.encoded] = handle
        return handle

    def _label_set_for(self, label_set: LabelSet) -> LabelSet:
        """Returns an appropriate `LabelSet` based off this metric's `meter`

        If this metric's `meter` is the same as label_set's meter, that means
        label_set was created from this metric's `meter` instance and the
        proper handle can be found. If not, label_set was created using a
        different `meter` implementation, in which the metric cannot interpret.
        In this case, return the `EMPTY_LABEL_SET`.

        Args:
            label_set: The `LabelSet` to check for the same `Meter` implentation.
        """
        if label_set.meter and label_set.meter is self.meter:
            return label_set
        return EMPTY_LABEL_SET

    def __repr__(self):
        return '{}(name="{}", description={})'.format(
            type(self).__name__, self.name, self.description
        )

    UPDATE_FUNCTION = lambda x, y: None  # noqa: E731


class Counter(Metric, metrics_api.Counter):
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
        meter: "Meter",
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = True,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            meter,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def add(self, label_set: LabelSet, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.Counter.add`."""
        self.get_handle(label_set).add(value)

    UPDATE_FUNCTION = add


class Gauge(Metric, metrics_api.Gauge):
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
        meter: "Meter",
        label_keys: Sequence[str] = None,
        enabled: bool = True,
        monotonic: bool = False,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            meter,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def set(self, label_set: LabelSet, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.Gauge.set`."""
        self.get_handle(label_set).set(value)

    UPDATE_FUNCTION = set


class Measure(Metric, metrics_api.Measure):
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
        meter: "Meter",
        label_keys: Sequence[str] = None,
        enabled: bool = False,
        monotonic: bool = False,
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            meter,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def record(self, label_set: LabelSet, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.Measure.record`."""
        self.get_handle(label_set).record(value)

    UPDATE_FUNCTION = record


# Singleton of meter.get_label_set() with zero arguments
EMPTY_LABEL_SET = LabelSet()


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`."""

    def __init__(self):
        self.labels = {}

    def record_batch(
        self,
        label_set: LabelSet,
        record_tuples: Sequence[Tuple[metrics_api.Metric, metrics_api.ValueT]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        for metric, value in record_tuples:
            metric.UPDATE_FUNCTION(label_set, value)

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
        # Ignore type b/c of mypy bug in addition to missing annotations
        return metric_type(  # type: ignore
            name,
            description,
            unit,
            value_type,
            self,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
        )

    def get_label_set(self, labels: Dict[str, str]):
        """See `opentelemetry.metrics.Meter.create_metric`.

        This implementation encodes the labels to use as a map key.

        Args:
            labels: The dictionary of label keys to label values.
        """
        if len(labels) == 0:
            return EMPTY_LABEL_SET
        sorted_labels = OrderedDict(sorted(labels.items()))
        # Uses statsd encoding for labels
        encoded = "," + ",".join(
            "%s=%s" % (key, value) for (key, value) in sorted_labels.items()
        )
        # If LabelSet exists for this meter in memory, use existing one
        if not self.labels.get(encoded):
            self.labels[encoded] = LabelSet(
                self, labels=sorted_labels, encoded=encoded
            )
        return self.labels[encoded]


meter = Meter()
