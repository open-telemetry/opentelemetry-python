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
from opentelemetry.sdk.metrics.export.aggregate import Aggregator
from opentelemetry.sdk.metrics.export.batcher import Batcher, UngroupedBatcher
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


# pylint: disable=redefined-outer-name
class LabelSet(metrics_api.LabelSet):
    """See `opentelemetry.metrics.LabelSet`."""

    def __init__(self, labels: Dict[str, str] = None, encoded=""):
        self.labels = labels
        self.encoded = encoded

    def __hash__(self):
        return hash(self.encoded)

    def __eq__(self, other):
        return self.encoded == other.encoded


class BaseHandle:
    """The base handle class containing common behavior for all handles.

    Handles are responsible for operating on data for metric instruments for a
    specific set of labels.

    Args:
        value_type: The type of values this handle holds (int, float).
        enabled: True if the originating instrument is enabled.
        monotonic: Indicates acceptance of only monotonic/non-monotonic values
            for updating counter and gauge handles.
        absolute: Indicates acceptance of negative updates to measure handles.
        aggregator: The aggregator for this handle. Will handle aggregation
            upon updates and checkpointing of values for exporting.
    """

    def __init__(
        self,
        value_type: Type[metrics_api.ValueT],
        enabled: bool,
        monotonic: bool,
        absolute: bool,
        aggregator: Aggregator,
    ):
        self.value_type = value_type
        self.enabled = enabled
        self.monotonic = monotonic
        self.absolute = absolute
        self.aggregator = aggregator
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

    def update(self, value: metrics_api.ValueT):
        self.last_update_timestamp = time_ns()
        self.aggregator.update(value)

    def __repr__(self):
        return '{}(data="{}", last_update_timestamp={})'.format(
            type(self).__name__,
            self.aggregator.current,
            self.last_update_timestamp,
        )


class CounterHandle(metrics_api.CounterHandle, BaseHandle):
    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.CounterHandle.add`."""
        if self._validate_update(value):
            if self.monotonic and value < 0:
                logger.warning("Monotonic counter cannot descend.")
                return
            self.update(value)


class GaugeHandle(metrics_api.GaugeHandle, BaseHandle):
    def set(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.GaugeHandle.set`."""
        if self._validate_update(value):
            if self.monotonic and value < self.aggregator.current:
                logger.warning("Monotonic gauge cannot descend.")
                return
            self.update(value)


class MeasureHandle(metrics_api.MeasureHandle, BaseHandle):
    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.MeasureHandle.record`."""
        if self._validate_update(value):
            if self.absolute and value < 0:
                logger.warning("Absolute measure cannot accept negatives.")
                return
            self.update(value)


class Metric(metrics_api.Metric):
    """Base class for all metric types.

    Also known as metric instrument. This is the class that is used to
    represent a metric that is to be continuously recorded and tracked. Each
    metric has a set of handles that are created from the metric. See
    `BaseHandle` for information on handles.
    """

    HANDLE_TYPE = BaseHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        label_keys: Sequence[str] = (),
        enabled: bool = True,
        monotonic: bool = False,
        absolute: bool = True,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.label_keys = label_keys
        self.enabled = enabled
        self.monotonic = monotonic
        self.absolute = absolute
        self.handles = {}

    def get_handle(self, label_set: LabelSet) -> BaseHandle:
        """See `opentelemetry.metrics.Metric.get_handle`."""
        handle = self.handles.get(label_set)
        if not handle:
            handle = self.HANDLE_TYPE(
                self.value_type,
                self.enabled,
                self.monotonic,
                self.absolute,
                # Aggregator will be created based off type of metric
                self.meter.batcher.aggregator_for(self.__class__),
            )
        self.handles[label_set] = handle
        return handle

    def __repr__(self):
        return '{}(name="{}", description={})'.format(
            type(self).__name__, self.name, self.description
        )

    UPDATE_FUNCTION = lambda x, y: None  # noqa: E731


class Counter(Metric, metrics_api.Counter):
    """See `opentelemetry.metrics.Counter`.

    By default, counter values can only go up (monotonic). Negative inputs
    will be rejected for monotonic counter metrics. Counter metrics that have a
    monotonic option set to False allows negative inputs.
    """

    HANDLE_TYPE = CounterHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        label_keys: Sequence[str] = (),
        enabled: bool = True,
        monotonic: bool = True,
        absolute: bool = False,
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
            absolute=absolute,
        )

    def add(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        """See `opentelemetry.metrics.Counter.add`."""
        self.get_handle(label_set).add(value)

    UPDATE_FUNCTION = add


class Gauge(Metric, metrics_api.Gauge):
    """See `opentelemetry.metrics.Gauge`.

    By default, gauge values can go both up and down (non-monotonic).
    Negative inputs will be rejected for monotonic gauge metrics.
    """

    HANDLE_TYPE = GaugeHandle

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        label_keys: Sequence[str] = (),
        enabled: bool = True,
        monotonic: bool = False,
        absolute: bool = False,
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
            absolute=absolute,
        )

    def set(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        """See `opentelemetry.metrics.Gauge.set`."""
        self.get_handle(label_set).set(value)

    UPDATE_FUNCTION = set


class Measure(Metric, metrics_api.Measure):
    """See `opentelemetry.metrics.Measure`."""

    HANDLE_TYPE = MeasureHandle

    def record(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        """See `opentelemetry.metrics.Measure.record`."""
        self.get_handle(label_set).record(value)

    UPDATE_FUNCTION = record


class Record:
    """Container class used for processing in the `Batcher`"""

    def __init__(
        self, metric: Metric, label_set: LabelSet, aggregator: Aggregator
    ):
        self.metric = metric
        self.label_set = label_set
        self.aggregator = aggregator


# Used when getting a LabelSet with no key/values
EMPTY_LABEL_SET = LabelSet()


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`.

    Args:
        batcher: The `Batcher` used for this meter.
    """

    def __init__(self, batcher: Batcher = UngroupedBatcher(True)):
        self.batcher = batcher
        # label_sets is a map of the labelset's encoded value to the label set
        self.label_sets = {}
        self.metrics = set()

    def collect(self) -> None:
        """Collects all the metrics created with this `Meter` for export.

        Utilizes the batcher to create checkpoints of the current values in
        each aggregator belonging to the metrics that were created with this
        meter instance.
        """
        for metric in self.metrics:
            if metric.enabled:
                for label_set, handle in metric.handles.items():
                    # Consider storing records in memory?
                    record = Record(metric, label_set, handle.aggregator)
                    # Checkpoints the current aggregators
                    # Applies different batching logic based on type of batcher
                    self.batcher.process(record)

    def record_batch(
        self,
        label_set: LabelSet,
        record_tuples: Sequence[Tuple[metrics_api.Metric, metrics_api.ValueT]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        for metric, value in record_tuples:
            metric.UPDATE_FUNCTION(value, label_set)

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        metric_type: Type[metrics_api.MetricT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
        monotonic: bool = False,
        absolute: bool = True,
    ) -> metrics_api.MetricT:
        """See `opentelemetry.metrics.Meter.create_metric`."""
        # Ignore type b/c of mypy bug in addition to missing annotations
        metric = metric_type(  # type: ignore
            name,
            description,
            unit,
            value_type,
            self,
            label_keys=label_keys,
            enabled=enabled,
            monotonic=monotonic,
            absolute=absolute,
        )
        self.metrics.add(metric)
        return metric

    def get_label_set(self, labels: Dict[str, str]):
        """See `opentelemetry.metrics.Meter.create_metric`.

        This implementation encodes the labels to use as a map key.

        Args:
            labels: The dictionary of label keys to label values.
        """
        if len(labels) == 0:
            return EMPTY_LABEL_SET
        # Use simple encoding for now until encoding API is implemented
        encoded = tuple(sorted(labels.items()))
        # If LabelSet exists for this meter in memory, use existing one
        if encoded not in self.label_sets:
            self.label_sets[encoded] = LabelSet(labels=labels, encoded=encoded)
        return self.label_sets[encoded]
