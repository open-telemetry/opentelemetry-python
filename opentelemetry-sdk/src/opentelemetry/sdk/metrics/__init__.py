# Copyright 2020, OpenTelemetry Authors
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
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


# pylint: disable=redefined-outer-name
class LabelSet(metrics_api.LabelSet):
    """See `opentelemetry.metrics.LabelSet`."""

    def __init__(self, labels: Dict[str, str] = None):
        if labels is None:
            labels = {}
        # LabelSet properties used only in dictionaries for fast lookup
        self._labels = tuple(labels.items())
        self._encoded = tuple(sorted(labels.items()))

    @property
    def labels(self):
        return self._labels

    def __hash__(self):
        return hash(self._encoded)

    def __eq__(self, other):
        return self._encoded == other._encoded


class BaseHandle:
    """The base handle class containing common behavior for all handles.

    Handles are responsible for operating on data for metric instruments for a
    specific set of labels.

    Args:
        value_type: The type of values this handle holds (int, float).
        enabled: True if the originating instrument is enabled.
        aggregator: The aggregator for this handle. Will handle aggregation
            upon updates and checkpointing of values for exporting.
    """

    def __init__(
        self,
        value_type: Type[metrics_api.ValueT],
        enabled: bool,
        aggregator: Aggregator,
    ):
        self.value_type = value_type
        self.enabled = enabled
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
            self.update(value)


class MeasureHandle(metrics_api.MeasureHandle, BaseHandle):
    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.MeasureHandle.record`."""
        if self._validate_update(value):
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
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.label_keys = label_keys
        self.enabled = enabled
        self.handles = {}

    def get_handle(self, label_set: LabelSet) -> BaseHandle:
        """See `opentelemetry.metrics.Metric.get_handle`."""
        handle = self.handles.get(label_set)
        if not handle:
            handle = self.HANDLE_TYPE(
                self.value_type,
                self.enabled,
                # Aggregator will be created based off type of metric
                self.meter.batcher.aggregator_for(self.__class__),
            )
            self.handles[label_set] = handle
        return handle

    def __repr__(self):
        return '{}(name="{}", description="{}")'.format(
            type(self).__name__, self.name, self.description
        )

    UPDATE_FUNCTION = lambda x, y: None  # noqa: E731


class Counter(Metric, metrics_api.Counter):
    """See `opentelemetry.metrics.Counter`.
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
    ):
        super().__init__(
            name,
            description,
            unit,
            value_type,
            meter,
            label_keys=label_keys,
            enabled=enabled,
        )

    def add(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        """See `opentelemetry.metrics.Counter.add`."""
        self.get_handle(label_set).add(value)

    UPDATE_FUNCTION = add


class Measure(Metric, metrics_api.Measure):
    """See `opentelemetry.metrics.Measure`."""

    HANDLE_TYPE = MeasureHandle

    def record(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        """See `opentelemetry.metrics.Measure.record`."""
        self.get_handle(label_set).record(value)

    UPDATE_FUNCTION = record


class Observer(metrics_api.Observer):
    """See `opentelemetry.metrics.Observer`."""

    def __init__(
        self,
        callback: metrics_api.ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ):
        self.callback = callback
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.label_keys = label_keys
        self.enabled = enabled

        self.aggregators = {}

    def observe(self, value: metrics_api.ValueT, label_set: LabelSet) -> None:
        if not self.enabled:
            return
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return

        if label_set not in self.aggregators:
            # TODO: how to cleanup aggregators?
            self.aggregators[label_set] = self.meter.batcher.aggregator_for(
                self.__class__
            )
        aggregator = self.aggregators[label_set]
        aggregator.update(value)

    def run(self) -> bool:
        try:
            self.callback(self)
        # pylint: disable=broad-except
        except Exception as exc:
            logger.warning(
                "Exception while executing observer callback: %s.", exc
            )
            return False
        return True

    def __repr__(self):
        return '{}(name="{}", description="{}")'.format(
            type(self).__name__, self.name, self.description
        )


class Record:
    """Container class used for processing in the `Batcher`"""

    def __init__(
        self,
        metric: metrics_api.MetricT,
        label_set: LabelSet,
        aggregator: Aggregator,
    ):
        self.metric = metric
        self.label_set = label_set
        self.aggregator = aggregator


# Used when getting a LabelSet with no key/values
EMPTY_LABEL_SET = LabelSet()


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`.

    Args:
        instrumentation_info: The `InstrumentationInfo` for this meter.
        stateful: Indicates whether the meter is stateful.
    """

    def __init__(
        self,
        instrumentation_info: "InstrumentationInfo",
        stateful: bool,
        resource: Resource = Resource.create_empty(),
    ):
        self.instrumentation_info = instrumentation_info
        self.metrics = set()
        self.observers = set()
        self.batcher = UngroupedBatcher(stateful)
        self.resource = resource

    def collect(self) -> None:
        """Collects all the metrics created with this `Meter` for export.

        Utilizes the batcher to create checkpoints of the current values in
        each aggregator belonging to the metrics that were created with this
        meter instance.
        """

        self._collect_metrics()
        self._collect_observers()

    def _collect_metrics(self) -> None:
        for metric in self.metrics:
            if metric.enabled:
                for label_set, handle in metric.handles.items():
                    # TODO: Consider storing records in memory?
                    record = Record(metric, label_set, handle.aggregator)
                    # Checkpoints the current aggregators
                    # Applies different batching logic based on type of batcher
                    self.batcher.process(record)

    def _collect_observers(self) -> None:
        for observer in self.observers:
            if not observer.enabled:
                continue

            # TODO: capture timestamp?
            if not observer.run():
                continue

            for label_set, aggregator in observer.aggregators.items():
                record = Record(observer, label_set, aggregator)
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
        )
        self.metrics.add(metric)
        return metric

    def register_observer(
        self,
        callback: metrics_api.ObserverCallbackT,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> metrics_api.Observer:
        ob = Observer(
            callback,
            name,
            description,
            unit,
            value_type,
            self,
            label_keys,
            enabled,
        )
        self.observers.add(ob)
        return ob

    def get_label_set(self, labels: Dict[str, str]):
        """See `opentelemetry.metrics.Meter.create_metric`.

        This implementation encodes the labels to use as a map key.

        Args:
            labels: The dictionary of label keys to label values.
        """
        if len(labels) == 0:
            return EMPTY_LABEL_SET
        return LabelSet(labels=labels)


class MeterProvider(metrics_api.MeterProvider):
    def __init__(
        self, resource: Resource = Resource.create_empty(),
    ):
        self.resource = resource

    def get_meter(
        self,
        instrumenting_module_name: str,
        stateful=True,
        instrumenting_library_version: str = "",
    ) -> "metrics_api.Meter":
        if not instrumenting_module_name:  # Reject empty strings too.
            raise ValueError("get_meter called with missing module name.")
        return Meter(
            InstrumentationInfo(
                instrumenting_module_name, instrumenting_library_version
            ),
            stateful=stateful,
            resource=self.resource,
        )
