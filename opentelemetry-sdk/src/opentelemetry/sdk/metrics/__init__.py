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

import atexit
import logging
import threading
from typing import Dict, Sequence, Tuple, Type

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    MetricsExporter,
)
from opentelemetry.sdk.metrics.export.aggregate import Aggregator
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController
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
        aggregator: Aggregator,
    ):
        self.value_type = value_type
        self.enabled = enabled
        self.aggregator = aggregator
        self._ref_count = 0
        self._ref_count_lock = threading.Lock()

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
        self.aggregator.update(value)

    def release(self):
        self.decrease_ref_count()

    def decrease_ref_count(self):
        with self._ref_count_lock:
            self._ref_count -= 1

    def increase_ref_count(self):
        with self._ref_count_lock:
            self._ref_count += 1

    def ref_count(self):
        with self._ref_count_lock:
            return self._ref_count

    def __repr__(self):
        return '{}(data="{}")'.format(
            type(self).__name__, self.aggregator.current
        )


class BoundCounter(metrics_api.BoundCounter, BaseBoundInstrument):
    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.BoundCounter.add`."""
        if self._validate_update(value):
            self.update(value)

    def _validate_update(self, value: metrics_api.ValueT) -> bool:
        if not super()._validate_update(value):
            return False
        if value < 0:
            logger.warning(
                "Invalid value %s passed to Counter, value must be non-negative. "
                "For a Counter that can decrease, use UpDownCounter.",
                value,
            )
            return False
        return True


class BoundUpDownCounter(metrics_api.BoundUpDownCounter, BaseBoundInstrument):
    def add(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.BoundUpDownCounter.add`."""
        if self._validate_update(value):
            self.update(value)


class BoundValueRecorder(metrics_api.BoundValueRecorder, BaseBoundInstrument):
    def record(self, value: metrics_api.ValueT) -> None:
        """See `opentelemetry.metrics.BoundValueRecorder.record`."""
        if self._validate_update(value):
            self.update(value)


class Metric(metrics_api.Metric):
    """Base class for all synchronous metric types.

    This is the class that is used to represent a metric that is to be
    synchronously recorded and tracked. Synchronous instruments are called
    inside a request, meaning they have an associated distributed context
    (i.e. Span context, correlation context). Multiple metric events may occur
    for a synchronous instrument within a give collection interval.

    Each metric has a set of bound metrics that are created from the metric.
    See `BaseBoundInstrument` for information on bound metric instruments.
    """

    BOUND_INSTR_TYPE = BaseBoundInstrument

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
                    # Aggregator will be created based off type of metric
                    self.meter.batcher.aggregator_for(self.__class__),
                )
                self.bound_instruments[key] = bound_instrument
        bound_instrument.increase_ref_count()
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
        bound_intrument.release()

    UPDATE_FUNCTION = add


class UpDownCounter(Metric, metrics_api.UpDownCounter):
    """See `opentelemetry.metrics.UpDownCounter`.
    """

    BOUND_INSTR_TYPE = BoundUpDownCounter

    def add(self, value: metrics_api.ValueT, labels: Dict[str, str]) -> None:
        """See `opentelemetry.metrics.UpDownCounter.add`."""
        bound_intrument = self.bind(labels)
        bound_intrument.add(value)
        bound_intrument.release()

    UPDATE_FUNCTION = add


class ValueRecorder(Metric, metrics_api.ValueRecorder):
    """See `opentelemetry.metrics.ValueRecorder`."""

    BOUND_INSTR_TYPE = BoundValueRecorder

    def record(
        self, value: metrics_api.ValueT, labels: Dict[str, str]
    ) -> None:
        """See `opentelemetry.metrics.ValueRecorder.record`."""
        bound_intrument = self.bind(labels)
        bound_intrument.record(value)
        bound_intrument.release()

    UPDATE_FUNCTION = record


class Observer(metrics_api.Observer):
    """Base class for all asynchronous metric types.

    Also known as Observers, observer metric instruments are asynchronous in
    that they are reported by a callback, once per collection interval, and
    lack context. They are permitted to report only one value per distinct
    label set per period.
    """

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

    def observe(
        self, value: metrics_api.ValueT, labels: Dict[str, str]
    ) -> None:
        key = get_labels_as_key(labels)
        if not self._validate_observe(value, key):
            return

        if key not in self.aggregators:
            # TODO: how to cleanup aggregators?
            self.aggregators[key] = self.meter.batcher.aggregator_for(
                self.__class__
            )
        aggregator = self.aggregators[key]
        aggregator.update(value)

    # pylint: disable=W0613
    def _validate_observe(
        self, value: metrics_api.ValueT, key: Tuple[Tuple[str, str]],
    ) -> bool:
        if not self.enabled:
            return False
        if not isinstance(value, self.value_type):
            logger.warning(
                "Invalid value passed for %s.", self.value_type.__name__
            )
            return False

        return True

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


class SumObserver(Observer, metrics_api.SumObserver):
    """See `opentelemetry.metrics.SumObserver`."""

    def _validate_observe(
        self, value: metrics_api.ValueT, key: Tuple[Tuple[str, str]],
    ) -> bool:
        if not super()._validate_observe(value, key):
            return False
        # Must be non-decreasing because monotonic
        if (
            key in self.aggregators
            and self.aggregators[key].current is not None
        ):
            if value < self.aggregators[key].current:
                logger.warning("Value passed must be non-decreasing.")
                return False
        return True


class UpDownSumObserver(Observer, metrics_api.UpDownSumObserver):
    """See `opentelemetry.metrics.UpDownSumObserver`."""


class ValueObserver(Observer, metrics_api.ValueObserver):
    """See `opentelemetry.metrics.ValueObserver`."""


class Record:
    """Container class used for processing in the `Batcher`"""

    def __init__(
        self,
        instrument: metrics_api.InstrumentT,
        labels: Dict[str, str],
        aggregator: Aggregator,
    ):
        self.instrument = instrument
        self.labels = labels
        self.aggregator = aggregator


class Meter(metrics_api.Meter):
    """See `opentelemetry.metrics.Meter`.

    Args:
        source: The `MeterProvider` that created this meter.
        instrumentation_info: The `InstrumentationInfo` for this meter.
    """

    def __init__(
        self,
        source: "MeterProvider",
        instrumentation_info: "InstrumentationInfo",
    ):
        self.instrumentation_info = instrumentation_info
        self.batcher = UngroupedBatcher(source.stateful)
        self.resource = source.resource
        self.metrics = set()
        self.observers = set()
        self.observers_lock = threading.Lock()

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

            to_remove = []

            with metric.bound_instruments_lock:
                for labels, bound_instr in metric.bound_instruments.items():
                    # TODO: Consider storing records in memory?
                    record = Record(metric, labels, bound_instr.aggregator)
                    # Checkpoints the current aggregators
                    # Applies different batching logic based on type of batcher
                    self.batcher.process(record)

                    if bound_instr.ref_count() == 0:
                        to_remove.append(labels)

                # Remove handles that were released
                for labels in to_remove:
                    del metric.bound_instruments[labels]

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
        observer_type=Type[metrics_api.ObserverT],
        label_keys: Sequence[str] = (),
        enabled: bool = True,
    ) -> metrics_api.Observer:
        ob = observer_type(
            callback,
            name,
            description,
            unit,
            value_type,
            self,
            label_keys,
            enabled,
        )
        with self.observers_lock:
            self.observers.add(ob)
        return ob

    def unregister_observer(self, observer: metrics_api.Observer) -> None:
        with self.observers_lock:
            self.observers.remove(observer)


class MeterProvider(metrics_api.MeterProvider):
    """See `opentelemetry.metrics.MeterProvider`.

    Args:
        stateful: Indicates whether meters created are going to be stateful
        resource: Resource for this MeterProvider
        shutdown_on_exit: Register an atexit hook to shut down when the
            application exists
    """

    def __init__(
        self,
        stateful=True,
        resource: Resource = Resource.create_empty(),
        shutdown_on_exit: bool = True,
    ):
        self.stateful = stateful
        self.resource = resource
        self._controllers = []
        self._exporters = set()
        self._atexit_handler = None
        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)

    def get_meter(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "metrics_api.Meter":
        """See `opentelemetry.metrics.MeterProvider`.get_meter."""
        if not instrumenting_module_name:  # Reject empty strings too.
            instrumenting_module_name = "ERROR:MISSING MODULE NAME"
            logger.error("get_meter called with missing module name.")
        return Meter(
            self,
            InstrumentationInfo(
                instrumenting_module_name, instrumenting_library_version,
            ),
        )

    def start_pipeline(
        self,
        meter: metrics_api.Meter,
        exporter: MetricsExporter = None,
        interval: float = 15.0,
    ) -> None:
        """Method to begin the collect/export pipeline.

        Args:
            meter: The meter to collect metrics from.
            exporter: The exporter to export metrics to.
            interval: The collect/export interval in seconds.
        """
        if not exporter:
            exporter = ConsoleMetricsExporter()
        self._exporters.add(exporter)
        # TODO: Controller type configurable?
        self._controllers.append(PushController(meter, exporter, interval))

    def shutdown(self) -> None:
        for controller in self._controllers:
            controller.shutdown()
        for exporter in self._exporters:
            exporter.shutdown()
        if self._atexit_handler is not None:
            atexit.unregister(self._atexit_handler)
            self._atexit_handler = None
