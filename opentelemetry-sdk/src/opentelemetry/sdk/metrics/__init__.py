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

import logging
import threading
from typing import Dict, Sequence, Tuple, Type

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk.metrics.export.aggregate import Aggregator
from opentelemetry.sdk.metrics.export.batcher import Batcher
from opentelemetry.sdk.metrics.view import view_manager, ViewData
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

logger = logging.getLogger(__name__)


def get_labels_as_key(labels: Dict[str, str]) -> Tuple[Tuple[str, str]]:
    """Gets a list of labels that can be used as a key in a dictionary."""
    return tuple(sorted(labels.items()))


class BaseBoundInstrument:
    """Class containing common behavior for all bound metric instruments.

    Bound metric instruments are responsible for operating on data for metric
    instruments for a specific set of labels.

    Args:
        value_type: The type of values for this bound instrument (int, float).
        enabled: True if the originating instrument is enabled.
        aggregator: The aggregator for this bound metric instrument. Will
            handle aggregation upon updates and checkpointing of values for
            exporting.
    """

    def __init__(
        self,
        value_type: Type[metrics_api.ValueT],
        enabled: bool,
        labels: Tuple[Tuple[str, str]],
        metric: metrics_api.MetricT,
    ):
        self._value_type = value_type
        self._enabled = enabled
        self._labels = labels
        self._metric = metric

    def _validate_update(self, value: metrics_api.ValueT) -> bool:
        if not self._enabled:
            return False
        if not isinstance(value, self._value_type):
            logger.warning(
                "Invalid value passed for %s.", self._value_type.__name__
            )
            return False
        return True

    def update(self, value: metrics_api.ValueT):
        # The view manager handles all updates to aggregators
        view_manager.update_view(self._metric, self._labels, value)

class BoundCounter(metrics_api.BoundCounter, BaseBoundInstrument):
    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.BoundCounter.add`."""
        if self._validate_update(value):
            self.update(value)


class BoundMeasure(metrics_api.BoundMeasure, BaseBoundInstrument):
    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.BoundMeasure.record`."""
        if self._validate_update(value):
            self.update(value)


class Metric(metrics_api.Metric):
    """Base class for all metric types.

    Also known as metric instrument. This is the class that is used to
    represent a metric that is to be continuously recorded and tracked. Each
    metric has a set of bound metrics that are created from the metric. See
    `BaseBoundInstrument` for information on bound metric instruments.
    """

    BOUND_INSTR_TYPE = BaseBoundInstrument

    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        meter: "Meter",
        enabled: bool = True,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.enabled = enabled
        self.bound_instruments = {}
        self.bound_instruments_lock = threading.Lock()

    def bind(self, labels: Dict[str, str]) -> BaseBoundInstrument:
        """See `opentelemetry.metrics.Metric.bind`."""
        key = get_labels_as_key(labels)
        with self.bound_instruments_lock:
            bound_instrument = self.bound_instruments.get(key)
            if bound_instrument is None:
                bound_instrument = self.BOUND_INSTR_TYPE(
                    self.value_type,
                    self.enabled,
                    get_labels_as_key(labels),
                    self,
                )
                self.bound_instruments[key] = bound_instrument
        return bound_instrument

    def __repr__(self):
        return '{}(name="{}", description="{}")'.format(
            type(self).__name__, self.name, self.description
        )

    UPDATE_FUNCTION = lambda x, y: None  # noqa: E731


class Counter(Metric, metrics_api.Counter):
    """See `opentelemetry.metrics.Counter`.
    """

    BOUND_INSTR_TYPE = BoundCounter

    def add(self, value: metrics_api.ValueT, labels: Dict[str, str]) -> None:
        """See `opentelemetry.metrics.Counter.add`."""
        bound_intrument = self.bind(labels)
        bound_intrument.add(value)

    UPDATE_FUNCTION = add


class Measure(Metric, metrics_api.Measure):
    """See `opentelemetry.metrics.Measure`."""

    BOUND_INSTR_TYPE = BoundMeasure

    def record(
        self, value: metrics_api.ValueT, labels: Dict[str, str]
    ) -> None:
        """See `opentelemetry.metrics.Measure.record`."""
        bound_intrument = self.bind(labels)
        bound_intrument.record(value)

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
        enabled: bool = True,
    ):
        self.callback = callback
        self.name = name
        self.description = description
        self.unit = unit
        self.value_type = value_type
        self.meter = meter
        self.enabled = enabled

        self.aggregators = {}

    def observe(
        self, value: metrics_api.ValueT, labels: Dict[str, str]
    ) -> None:
        if not self.enabled:
            return
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return

        key = get_labels_as_key(labels)
        if key not in self.aggregators:
            # TODO: how to cleanup aggregators?
            self.aggregators[key] = self.meter.batcher.aggregator_for(
                self.__class__
            )
        aggregator = self.aggregators[key]
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
        labels: Tuple[Tuple[str, str]],
        aggregator: Aggregator,
    ):
        self.metric = metric
        self.labels = labels
        self.aggregator = aggregator


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
        self.batcher = Batcher(stateful)
        self.observers_lock = threading.Lock()
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
            if not metric.enabled:
                continue
            
            for view_data in view_manager.get_all_view_data_for_metric(metric):
                record = Record(metric, view_data.labels, view_data.aggregator)
                # Checkpoints the current aggregators
                # Applies different logic for stateful
                self.batcher.process(record)

    def _collect_observers(self) -> None:
        with self.observers_lock:
            for observer in self.observers:
                if not observer.enabled:
                    continue

                if not observer.run():
                    continue

                for labels, aggregator in observer.aggregators.items():
                    record = Record(observer, labels, aggregator)
                    self.batcher.process(record)

    def record_batch(
        self,
        labels: Dict[str, str],
        record_tuples: Sequence[Tuple[metrics_api.Metric, metrics_api.ValueT]],
    ) -> None:
        """See `opentelemetry.metrics.Meter.record_batch`."""
        # TODO: Avoid enconding the labels for each instrument, encode once
        # and reuse.
        for metric, value in record_tuples:
            metric.UPDATE_FUNCTION(value, labels)

    def create_metric(
        self,
        name: str,
        description: str,
        unit: str,
        value_type: Type[metrics_api.ValueT],
        metric_type: Type[metrics_api.MetricT],
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
        enabled: bool = True,
    ) -> metrics_api.Observer:
        ob = Observer(
            callback,
            name,
            description,
            unit,
            value_type,
            self,
            enabled,
        )
        with self.observers_lock:
            self.observers.add(ob)
        return ob

    def unregister_observer(self, observer: "Observer") -> None:
        with self.observers_lock:
            self.observers.remove(observer)


class MeterProvider(metrics_api.MeterProvider):
    def __init__(self, resource: Resource = Resource.create_empty()):
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
