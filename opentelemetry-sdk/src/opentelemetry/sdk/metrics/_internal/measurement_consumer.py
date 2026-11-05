# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Where a measurement goes once an instrument has produced it.

A ``MeterProvider`` owns one ``SynchronousMeasurementConsumer``, which holds a
``MetricReaderStorage`` per registered reader. Every measurement recorded on a
synchronous instrument is offered to all of them, so each reader aggregates it
on its own terms. Collection runs the other way round: a single reader asks
for its own storage, and the asynchronous instruments registered on the
provider are polled at that moment.

"Synchronous" in ``SynchronousMeasurementConsumer`` describes the consumer and
not the instruments: it aggregates on the thread that recorded the
measurement, with no queue in between.
"""

# pylint: disable=unused-import

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from logging import getLogger
from threading import Lock
from time import time_ns

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
import opentelemetry.sdk.metrics._internal.instrument
from opentelemetry.metrics._internal.instrument import CallbackOptions
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.metric_reader_storage import (
    MetricReaderStorage,
)
from opentelemetry.sdk.metrics._internal.point import (
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.resources import Resource

_logger = getLogger(__name__)


class MeasurementConsumer(ABC):
    """What a ``MeterProvider`` routes its measurements to.

    An implementation accepts measurements from synchronous instruments, keeps
    a register of the asynchronous instruments so they can be polled, and
    produces a batch for one reader on demand.
    ``SynchronousMeasurementConsumer`` is the only implementation in the SDK.
    """

    @abstractmethod
    def consume_measurement(self, measurement: Measurement) -> None:
        """Take one measurement recorded on a synchronous instrument.

        Called on the thread that recorded it, so an implementation that
        blocks here blocks the instrumented application.

        Args:
            measurement: The measurement, which names the instrument it came
                from.
        """

    @abstractmethod
    def register_asynchronous_instrument(
        self,
        instrument: ("opentelemetry.sdk.metrics._internal.instrument._Asynchronous"),
    ):
        """Record that an asynchronous instrument exists.

        The instrument records nothing by itself. Registering it is what gets
        its callbacks run at collection time.

        Args:
            instrument: The observable counter, observable up down counter or
                observable gauge to poll from now on.
        """

    @abstractmethod
    def collect(
        self,
        metric_reader: "opentelemetry.sdk.metrics.export.MetricReader",
        timeout_millis: float = 10_000,
    ) -> MetricsData | None:
        """Produce the batch one reader should export.

        Args:
            metric_reader: The reader asking. Only the state held for this
                reader is collected, and the other readers are untouched.
            timeout_millis: How long the whole collection may take, in
                milliseconds, including the callbacks of every asynchronous
                instrument.

        Returns:
            The batch, or ``None`` when nothing was aggregated for this reader
            since the last collection.
        """


class SynchronousMeasurementConsumer(MeasurementConsumer):
    """Aggregates each measurement on the thread that recorded it.

    One ``MetricReaderStorage`` is held per reader, built from the
    temporality, aggregation and cardinality limit mappings the reader was
    configured with. A measurement is offered to every storage in turn, which
    is why two readers can report the same instrument differently.

    The mapping of readers to storages is replaced wholesale rather than
    mutated whenever a reader is added or removed, so recording a measurement
    takes no lock and never sees a half updated mapping. Collection and
    registration do take the lock.

    Args:
        sdk_config: The provider's configuration, passed on to every storage
            and consulted for the exemplar filter that decides whether a
            measurement may be kept as an exemplar.
        metric_readers: The readers to build storages for. Iterated once, at
            construction. Readers registered later arrive through
            ``add_metric_reader``.
    """

    def __init__(
        self,
        sdk_config: "opentelemetry.sdk.metrics._internal.sdk_configuration.SdkConfiguration",
        metric_readers: Iterable["opentelemetry.sdk.metrics.MetricReader"],
    ) -> None:
        """Build the instance and one storage per reader.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._lock = Lock()
        self._sdk_config = sdk_config
        self._reader_storages: Mapping[opentelemetry.sdk.metrics.export.MetricReader, MetricReaderStorage] = {
            reader: MetricReaderStorage(
                sdk_config,
                reader._instrument_class_temporality,
                reader._instrument_class_aggregation,
                reader._instrument_class_cardinality_limit,
            )
            for reader in metric_readers
        }
        self._async_instruments: list[opentelemetry.sdk.metrics._internal.instrument._Asynchronous] = []

    def consume_measurement(self, measurement: Measurement) -> None:
        """Offer one measurement to the storage of every registered reader.

        The exemplar filter is applied once here and its verdict is passed to
        all of the storages, so every reader agrees on whether this particular
        measurement is exemplar material.

        With no reader registered the measurement is dropped, since there is
        nothing to aggregate it into.

        Args:
            measurement: The measurement to aggregate.
        """
        should_sample_exemplar = self._sdk_config.exemplar_filter.should_sample(
            measurement.value,
            measurement.time_unix_nano,
            measurement.attributes,
            measurement.context,
        )
        # `_reader_storages` is replaced (never mutated in place) by
        # `add_metric_reader` and `remove_metric_reader`, so it is safe
        # to iterate over without a lock.
        for reader_storage in self._reader_storages.values():
            reader_storage.consume_measurement(measurement, should_sample_exemplar)

    def register_asynchronous_instrument(
        self,
        instrument: ("opentelemetry.sdk.metrics._internal.instrument._Asynchronous"),
    ) -> None:
        """Add an asynchronous instrument to the list polled at collection.

        Nothing checks for a duplicate, so registering the same instrument
        twice has its callbacks run twice per collection.

        Args:
            instrument: The instrument to poll from the next collection on.
        """
        with self._lock:
            self._async_instruments.append(instrument)

    def collect(
        self,
        metric_reader: "opentelemetry.sdk.metrics.export.MetricReader",
        timeout_millis: float = 10_000,
    ) -> MetricsData | None:
        """Poll the asynchronous instruments, then collect for one reader.

        The callback of every registered asynchronous instrument is run, and
        the measurements they yield are aggregated into the storage of this
        reader alone, so a reader that never collects never sees them. A
        callback is told how long it has left only once the remaining budget
        has fallen below ten seconds, and nothing interrupts a callback that
        runs past the deadline: the deadline is tested after each instrument
        has been fully iterated.

        The metrics of the reader's metric producers are collected afterwards
        and merged into the batch, under the resource of the SDK's own
        ``ResourceMetrics`` when there is one and under the provider's
        resource otherwise.

        The whole call holds the consumer's lock, so two readers collecting at
        the same time run one after the other, and a reader cannot be added or
        removed while a collection is in progress.

        Args:
            metric_reader: The reader to collect for. It has to be registered
                on this consumer.
            timeout_millis: The budget for the whole call, in milliseconds,
                shared by the asynchronous callbacks and the metric producers.

        Returns:
            The batch for this reader, or ``None`` when neither the reader's
            storage nor its metric producers yielded anything.

        Raises:
            MetricsTimeoutError: If the budget is spent after an asynchronous
                callback has run. The measurements that callback produced were
                already aggregated into the reader's storage and stay there,
                since raising skips the ``collect`` call that would have
                drained it. They are not reported by this collection and are
                aggregated again by the next one, which for an asynchronous
                counter reports a total larger than anything the callback
                observed.
            KeyError: If the reader is not registered on this consumer.
        """
        with self._lock:
            metric_reader_storage = self._reader_storages[metric_reader]
            # for now, just use the defaults
            callback_options = CallbackOptions()
            deadline_ns = time_ns() + (timeout_millis * 1e6)

            default_timeout_ns = 10000 * 1e6

            for async_instrument in self._async_instruments:
                remaining_time = deadline_ns - time_ns()

                if remaining_time < default_timeout_ns:
                    callback_options = CallbackOptions(timeout_millis=remaining_time / 1e6)

                # callback() is a generator function: the user callback
                # only runs while the loop below iterates it, so the
                # deadline can only be observed after iteration completes.
                for measurement in async_instrument.callback(callback_options):
                    should_sample_exemplar = self._sdk_config.exemplar_filter.should_sample(
                        measurement.value,
                        measurement.time_unix_nano,
                        measurement.attributes,
                        measurement.context,
                    )
                    metric_reader_storage.consume_measurement(measurement, should_sample_exemplar)

                if time_ns() >= deadline_ns:
                    raise MetricsTimeoutError(
                        f"Timed out while executing callback for instrument {async_instrument.name}"
                    )

            result = self._reader_storages[metric_reader].collect()

            if producer_scope_metrics := self._collect_from_producers(metric_reader, deadline_ns):
                result = self._merge_producer_metrics(result, producer_scope_metrics, self._sdk_config.resource)

        return result

    @staticmethod
    def _collect_from_producers(
        metric_reader: "opentelemetry.sdk.metrics.export.MetricReader",
        deadline_ns: float,
    ) -> list[ScopeMetrics]:
        """Collect ScopeMetrics from the reader's MetricProducers.

        Called while holding ``self._lock`` so ``produce()`` calls are
        serialized. A producer that fails or times out is isolated so
        metrics collected by the SDK are not dropped.

        Each producer is given whatever is left of the deadline. Once nothing
        is left, the remaining producers are skipped with a single warning,
        and the producers already polled keep their metrics.

        Args:
            metric_reader: The reader whose registered producers are polled,
                in the order they were passed to it.
            deadline_ns: When the whole collection has to be finished, as a
                time in nanoseconds since the epoch.

        Returns:
            The metrics of every producer that answered in time, concatenated.
            Empty when the reader has no producers, when all of them failed,
            or when the deadline had already passed.
        """
        producer_scope_metrics: list[ScopeMetrics] = []
        # pylint: disable-next=protected-access
        for producer in metric_reader._metric_producers:
            remaining_millis = (deadline_ns - time_ns()) / 1e6
            if remaining_millis <= 0:
                _logger.warning("Timed out collecting from metric producers, skipping remaining producers.")
                break

            try:
                scopes = list(producer.produce(timeout_millis=remaining_millis))
            # pylint: disable-next=broad-except
            except Exception:
                _logger.exception(
                    "Metric producer %s failed to produce metrics, skipping.",
                    producer,
                )
                continue

            producer_scope_metrics.extend(scopes)

        return producer_scope_metrics

    @staticmethod
    def _merge_producer_metrics(
        result: MetricsData | None,
        producer_scope_metrics: list[ScopeMetrics],
        resource: Resource,
    ) -> MetricsData:
        """Put the producers' metrics into the batch the SDK collected.

        The producers' scopes are appended to the first ``ResourceMetrics`` of
        the batch, which means they are reported under the resource the SDK
        collected rather than one of their own. Any further
        ``ResourceMetrics`` is carried over untouched.

        Args:
            result: The batch the reader's storage produced, which is ``None``
                when it had nothing to report.
            producer_scope_metrics: The scopes gathered from the producers.
            resource: The provider's resource, used only when ``result`` holds
                no ``ResourceMetrics`` to attach the scopes to.

        Returns:
            A batch holding both sets of metrics. A fresh one built around
            ``resource`` when ``result`` had nothing, otherwise a copy of
            ``result`` whose first ``ResourceMetrics`` has grown.
        """
        if result is not None and result.resource_metrics:
            sdk_resource_metrics = result.resource_metrics[0]
            merged = ResourceMetrics(
                resource=sdk_resource_metrics.resource,
                scope_metrics=[
                    *sdk_resource_metrics.scope_metrics,
                    *producer_scope_metrics,
                ],
                schema_url=sdk_resource_metrics.schema_url,
            )
            return MetricsData(resource_metrics=[merged, *result.resource_metrics[1:]])

        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=resource,
                    scope_metrics=producer_scope_metrics,
                    schema_url=resource.schema_url,
                )
            ]
        )

    def add_metric_reader(self, metric_reader: "opentelemetry.sdk.metrics.MetricReader") -> None:
        """Registers a new metric reader.

        A storage is built for the reader from the temporality, aggregation
        and cardinality limit mappings it carries, which means the reader
        starts empty and reports nothing recorded before this call. Adding a
        reader that is already registered replaces its storage and discards
        everything aggregated in it so far.

        Args:
            metric_reader: The reader to start aggregating for.
        """
        # Build a new mapping and swap it in atomically so that
        # a concurrent consume_measurement never iterates a mapping
        # that is being mutated in place.
        with self._lock:
            new_reader_storages = dict(self._reader_storages)
            new_reader_storages[metric_reader] = MetricReaderStorage(
                self._sdk_config,
                # pylint: disable-next=protected-access
                metric_reader._instrument_class_temporality,
                # pylint: disable-next=protected-access
                metric_reader._instrument_class_aggregation,
                # pylint: disable-next=protected-access
                metric_reader._instrument_class_cardinality_limit,
            )
            self._reader_storages = new_reader_storages

    def remove_metric_reader(self, metric_reader: "opentelemetry.sdk.metrics.MetricReader") -> None:
        """Unregisters the given metric reader.

        The reader's storage is dropped along with everything aggregated in
        it, so measurements recorded but not yet collected are lost.

        Args:
            metric_reader: The reader to stop aggregating for.

        Raises:
            KeyError: If the reader is not registered on this consumer.
        """
        # Mutate using copy-on-write: see add_metric_reader.
        with self._lock:
            new_reader_storages = dict(self._reader_storages)
            new_reader_storages.pop(metric_reader)
            self._reader_storages = new_reader_storages
