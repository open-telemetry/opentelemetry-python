# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import math
import os
import weakref
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from logging import getLogger
from os import environ, linesep
from sys import stdout
from threading import Event, Lock, RLock, Thread
from time import perf_counter, time_ns
from typing import IO

from typing_extensions import final

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics._internal
from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.metrics import MeterProvider, NoOpMeterProvider
from opentelemetry.sdk.environment_variables import (
    OTEL_METRIC_EXPORT_INTERVAL,
    OTEL_METRIC_EXPORT_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _DEFAULT_CARDINALITY_LIMIT,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    AggregationTemporality,
    DefaultAggregation,
)
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.instrument import (
    Counter,
    Gauge,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.point import (
    MetricsData,
    ScopeMetrics,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.util._once import Once

from ._metric_reader_metrics import create_metric_reader_metrics

_logger = getLogger(__name__)


class MetricExportResult(Enum):
    """Result of exporting a metric

    Can be any of the following values:"""

    SUCCESS = 0
    FAILURE = 1


class MetricExporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export metrics received
    in their own format.

    Args:
        preferred_temporality: Used by `opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader` to
            configure exporter level preferred temporality. See `opentelemetry.sdk.metrics.export.MetricReader` for
            more details on what preferred temporality is.
        preferred_aggregation: Used by `opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader` to
            configure exporter level preferred aggregation. See `opentelemetry.sdk.metrics.export.MetricReader` for
            more details on what preferred aggregation is.
    """

    def __init__(
        self,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, opentelemetry.sdk.metrics.view.Aggregation] | None = None,
    ) -> None:
        self._preferred_temporality = preferred_temporality
        self._preferred_aggregation = preferred_aggregation

    @abstractmethod
    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Exports a batch of telemetry data.

        Args:
            metrics_data: The collected batch, holding one ``ResourceMetrics``
                per resource, each holding ``ScopeMetrics`` and ``Metric``.
            timeout_millis: How long the export may take, in milliseconds.
                Enforcing it is left to the implementation.
            **kwargs: Ignored by the exporters in this package, and there for
                a caller to pass something an individual exporter understands.

        Returns:
            The result of the export
        """

    @abstractmethod
    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """
        Ensure that export of any metrics currently received by the exporter
        are completed as soon as possible.

        Args:
            timeout_millis: How long the flush may take, in milliseconds.

        Returns:
            Whether everything held was exported within the timeout.
        """

    @abstractmethod
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.

        Args:
            timeout_millis: How long the shutdown may take, in milliseconds.
            **kwargs: Accepted and ignored by the exporters in this package.
        """


class ConsoleMetricExporter(MetricExporter):
    """Implementation of :class:`MetricExporter` that prints metrics to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.

    Args:
        out: Where to write. The default is bound when this module is imported
            rather than when an exporter is built, so replacing ``sys.stdout``
            at any point after that import does not redirect an exporter built
            with the default. Pass the stream explicitly to write anywhere
            else.
        formatter: Turns one batch into the text to write. The default emits
            the indented JSON of ``MetricsData.to_json``, which spans several
            lines, followed by a line separator. Pass a formatter calling
            ``to_json(indent=None)`` for the single-line form a line-delimited
            consumer wants. The text is written as given, so a formatter that
            appends no separator runs batches together.
        preferred_temporality: The temporality per instrument class a reader
            built with this exporter adopts. ``None`` leaves that reader on
            its own defaults.
        preferred_aggregation: The aggregation per instrument class a reader
            built with this exporter adopts. ``None`` leaves that reader on
            its own defaults.
    """

    def __init__(
        self,
        out: IO = stdout,
        formatter: Callable[[MetricsData], str] = lambda metrics_data: metrics_data.to_json() + linesep,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, opentelemetry.sdk.metrics.view.Aggregation] | None = None,
    ):
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )
        self.out = out
        self.formatter = formatter

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        """Format the batch and write it to the stream.

        Args:
            metrics_data: The batch to write.
            timeout_millis: Ignored. The write is not bounded by a timeout.
            **kwargs: Ignored.

        Returns:
            Always ``MetricExportResult.SUCCESS``. An error raised by the
            stream or by the formatter propagates instead of being turned into
            a failure result.
        """
        self.out.write(self.formatter(metrics_data))
        self.out.flush()
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Do nothing, leaving the stream open since it was not opened here.

        Args:
            timeout_millis: Ignored.
            **kwargs: Ignored.
        """

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Do nothing, since ``export`` already flushed every batch.

        Args:
            timeout_millis: Ignored.

        Returns:
            Always ``True``.
        """
        return True


InstrumentCardinalityKey = (
    type[Counter]
    | type[UpDownCounter]
    | type[Histogram]
    | type[Gauge]
    | type[ObservableCounter]
    | type[ObservableUpDownCounter]
    | type[ObservableGauge]
)

CardinalityLimits = dict[InstrumentCardinalityKey, int]

_CARDINALITY_INSTRUMENT_CLASSES: dict[type, type] = {
    Counter: _Counter,
    UpDownCounter: _UpDownCounter,
    Histogram: _Histogram,
    Gauge: _Gauge,
    ObservableCounter: _ObservableCounter,
    ObservableUpDownCounter: _ObservableUpDownCounter,
    ObservableGauge: _ObservableGauge,
}


def _validate_cardinality_limit(typ: type, limit: int) -> type:
    """Return the SDK instrument class for ``typ`` after validating ``limit``."""
    if typ not in _CARDINALITY_INSTRUMENT_CLASSES:
        raise ValueError(f"Invalid instrument class found {typ}")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError(f"Cardinality limit for {typ} must be a positive integer, got {limit!r}")
    return _CARDINALITY_INSTRUMENT_CLASSES[typ]


class MetricProducer(ABC):
    """Interface bridging third-party metric sources into a :class:`MetricReader`.

    An implementation is registered on a ``MetricReader`` (via its
    ``metric_producers`` argument) and its metrics are collected alongside the
    SDK's own internal state whenever the reader collects. See the OpenTelemetry
    metrics SDK specification on
    `MetricProducer <https://opentelemetry.io/docs/specs/otel/metrics/sdk/#metricproducer>`__.
    """

    @abstractmethod
    def produce(self, timeout_millis: float = 10_000) -> Iterable[ScopeMetrics]:
        """Returns the producer's metrics as an iterable of ``ScopeMetrics``.

        A producer SHOULD emit a single ``InstrumentationScope`` that identifies
        the producer itself.

        Args:
            timeout_millis: Amount of time in milliseconds before the produce
                operation should time out.

        Returns:
            An iterable of :class:`~opentelemetry.sdk.metrics.export.ScopeMetrics`.
        """


class MetricReader(ABC):
    # pylint: disable=too-many-branches,broad-exception-raised
    """
    Base class for all metric readers

    Args:
        preferred_temporality: A mapping between instrument classes and
            aggregation temporality. By default uses CUMULATIVE for all instrument
            classes. This mapping will be used to define the default aggregation
            temporality of every instrument class. If the user wants to make a
            change in the default aggregation temporality of an instrument class,
            it is enough to pass here a dictionary whose keys are the instrument
            classes and the values are the corresponding desired aggregation
            temporalities of the classes that the user wants to change, not all of
            them. The classes not included in the passed dictionary will retain
            their association to their default aggregation temporalities.
        preferred_aggregation: A mapping between instrument classes and
            aggregation instances. By default maps all instrument classes to an
            instance of `DefaultAggregation`. This mapping will be used to
            define the default aggregation of every instrument class. If the
            user wants to make a change in the default aggregation of an
            instrument class, it is enough to pass here a dictionary whose keys
            are the instrument classes and the values are the corresponding
            desired aggregation for the instrument classes that the user wants
            to change, not necessarily all of them. The classes not included in
            the passed dictionary will retain their association to their
            default aggregations. The aggregation defined here will be
            overridden by an aggregation defined by a view that is not
            `DefaultAggregation`.
        metric_producers: A sequence of `MetricProducer` instances that bridge
            third-party metric sources. Their metrics are collected alongside
            the SDK's own metrics whenever this reader collects.
        cardinality_limits: A dictionary mapping instrument classes to the
            maximum number of distinct attribute sets a metric stream of that
            instrument class holds at once. They are released on collection
            only for a synchronous instrument collected with delta
            temporality, so under the default cumulative preference the limit
            is spent over the life of the stream rather than per collection
            cycle. Instrument classes not included use a limit of 2000. A
            limit defined by a view takes precedence. Measurements with
            further attribute sets are aggregated into one additional point
            identified by the attribute ``otel.metric.overflow=true``.
        otel_component_type: The value reported as ``otel.component.type`` by
            the metrics the SDK emits about this reader. Defaults to the
            qualified name of the reader class, which is what a reader outside
            this package gets unless it names a value from the semantic
            conventions.

    .. document protected _receive_metrics which is a intended to be overridden by subclass
    .. automethod:: _receive_metrics
    """

    def __init__(
        self,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, opentelemetry.sdk.metrics.view.Aggregation] | None = None,
        cardinality_limits: CardinalityLimits | None = None,
        *,
        metric_producers: Sequence[MetricProducer] = (),
        otel_component_type: OtelComponentTypeValues | None = None,
    ) -> None:
        self._metric_producers: tuple[MetricProducer, ...] = tuple(metric_producers)
        self._collect: (
            Callable[
                [
                    opentelemetry.sdk.metrics.export.MetricReader,
                    AggregationTemporality,
                ],
                Iterable[opentelemetry.sdk.metrics.export.Metric],
            ]
            | None
        ) = None

        self._instrument_class_temporality = {
            _Counter: AggregationTemporality.CUMULATIVE,
            _UpDownCounter: AggregationTemporality.CUMULATIVE,
            _Histogram: AggregationTemporality.CUMULATIVE,
            _Gauge: AggregationTemporality.CUMULATIVE,
            _ObservableCounter: AggregationTemporality.CUMULATIVE,
            _ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            _ObservableGauge: AggregationTemporality.CUMULATIVE,
        }

        if preferred_temporality is not None:
            for temporality in preferred_temporality.values():
                if temporality not in (
                    AggregationTemporality.CUMULATIVE,
                    AggregationTemporality.DELTA,
                ):
                    raise Exception(f"Invalid temporality value found {temporality}")

        if preferred_temporality is not None:
            for typ, temporality in preferred_temporality.items():
                if typ is Counter:
                    self._instrument_class_temporality[_Counter] = temporality
                elif typ is UpDownCounter:
                    self._instrument_class_temporality[_UpDownCounter] = temporality
                elif typ is Histogram:
                    self._instrument_class_temporality[_Histogram] = temporality
                elif typ is Gauge:
                    self._instrument_class_temporality[_Gauge] = temporality
                elif typ is ObservableCounter:
                    self._instrument_class_temporality[_ObservableCounter] = temporality
                elif typ is ObservableUpDownCounter:
                    self._instrument_class_temporality[_ObservableUpDownCounter] = temporality
                elif typ is ObservableGauge:
                    self._instrument_class_temporality[_ObservableGauge] = temporality
                else:
                    raise Exception(f"Invalid instrument class found {typ}")

        self._preferred_temporality = preferred_temporality
        self._instrument_class_aggregation = {
            _Counter: DefaultAggregation(),
            _UpDownCounter: DefaultAggregation(),
            _Histogram: DefaultAggregation(),
            _Gauge: DefaultAggregation(),
            _ObservableCounter: DefaultAggregation(),
            _ObservableUpDownCounter: DefaultAggregation(),
            _ObservableGauge: DefaultAggregation(),
        }

        if preferred_aggregation is not None:
            for typ, aggregation in preferred_aggregation.items():
                if typ is Counter:
                    self._instrument_class_aggregation[_Counter] = aggregation
                elif typ is UpDownCounter:
                    self._instrument_class_aggregation[_UpDownCounter] = aggregation
                elif typ is Histogram:
                    self._instrument_class_aggregation[_Histogram] = aggregation
                elif typ is Gauge:
                    self._instrument_class_aggregation[_Gauge] = aggregation
                elif typ is ObservableCounter:
                    self._instrument_class_aggregation[_ObservableCounter] = aggregation
                elif typ is ObservableUpDownCounter:
                    self._instrument_class_aggregation[_ObservableUpDownCounter] = aggregation
                elif typ is ObservableGauge:
                    self._instrument_class_aggregation[_ObservableGauge] = aggregation
                else:
                    raise Exception(f"Invalid instrument class found {typ}")

        self._instrument_class_cardinality_limit = {
            _Counter: _DEFAULT_CARDINALITY_LIMIT,
            _UpDownCounter: _DEFAULT_CARDINALITY_LIMIT,
            _Histogram: _DEFAULT_CARDINALITY_LIMIT,
            _Gauge: _DEFAULT_CARDINALITY_LIMIT,
            _ObservableCounter: _DEFAULT_CARDINALITY_LIMIT,
            _ObservableUpDownCounter: _DEFAULT_CARDINALITY_LIMIT,
            _ObservableGauge: _DEFAULT_CARDINALITY_LIMIT,
        }

        if cardinality_limits is not None:
            for typ, limit in cardinality_limits.items():
                self._instrument_class_cardinality_limit[_validate_cardinality_limit(typ, limit)] = limit

        self._otel_component_type = otel_component_type.value if otel_component_type else type(self).__qualname__
        self._metrics = create_metric_reader_metrics(
            self._otel_component_type,
            NoOpMeterProvider(),
            parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )

    @final
    def collect(self, timeout_millis: float = 10_000) -> None:
        """Collects the metrics from the internal SDK state and
        invokes the `_receive_metrics` with the collection.

        Args:
            timeout_millis: Amount of time in milliseconds before this function
              raises a timeout error.

        If any of the underlying ``collect`` methods called by this method
        fails by any reason (including timeout) an exception will be raised
        detailing the individual errors that caused this function to fail.
        """
        if self._collect is None:
            _logger.warning("Cannot call collect on a MetricReader until it is registered on a MeterProvider")
            return

        start_time = perf_counter()
        try:
            metrics = self._collect(self, timeout_millis=timeout_millis)
        finally:
            self._metrics.record_collection(perf_counter() - start_time)

        if metrics is not None:
            self._receive_metrics(
                metrics,
                timeout_millis=timeout_millis,
            )

    @final
    def _set_collect_callback(
        self,
        func: Callable[
            [
                opentelemetry.sdk.metrics.export.MetricReader,
                AggregationTemporality,
            ],
            MetricsData,
        ]
        | None,
    ) -> None:
        """This function is internal to the SDK. It should not be called or overridden by users"""
        self._collect = func

    @abstractmethod
    def _receive_metrics(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        """Called by `MetricReader.collect` when it receives a batch of metrics"""

    def _set_meter_provider(self, meter_provider: MeterProvider) -> None:
        self._metrics = create_metric_reader_metrics(
            self._otel_component_type,
            meter_provider,
            parse_boolean_environment_variable(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED),
        )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Collect once, right now, instead of waiting for the next cycle.

        Args:
            timeout_millis: The budget for the collection, in milliseconds.

        Returns:
            Always ``True``, including when the reader is not registered on a
            ``MeterProvider`` and nothing was collected.
        """
        self.collect(timeout_millis=timeout_millis)
        return True

    @abstractmethod
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shuts down the MetricReader. This method provides a way
        for the MetricReader to do any cleanup required. A metric reader can
        only be shutdown once, any subsequent calls are ignored and return
        failure status.

        When a `MetricReader` is registered on a
        :class:`~opentelemetry.sdk.metrics.MeterProvider`,
        :meth:`~opentelemetry.sdk.metrics.MeterProvider.shutdown` will invoke this
        automatically.

        Args:
            timeout_millis: The budget for the whole shutdown, in
                milliseconds, final collection and thread join included.
            **kwargs: Accepted and ignored by the readers in this package.
        """


class InMemoryMetricReader(MetricReader):
    """Implementation of `MetricReader` that returns its metrics from :func:`get_metrics_data`.

    This is useful for e.g. unit tests.

    Args:
        preferred_temporality: The temporality per instrument class, as on
            ``MetricReader``.
        preferred_aggregation: The aggregation per instrument class, as on
            ``MetricReader``.
        cardinality_limits: The attribute set limit per instrument class, as
            on ``MetricReader``.
        metric_producers: Producers whose metrics are collected together with
            the SDK's own on every ``get_metrics_data`` call.
    """

    def __init__(
        self,
        preferred_temporality: dict[type, AggregationTemporality] | None = None,
        preferred_aggregation: dict[type, opentelemetry.sdk.metrics.view.Aggregation] | None = None,
        cardinality_limits: CardinalityLimits | None = None,
        *,
        metric_producers: Sequence[MetricProducer] = (),
    ) -> None:
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
            cardinality_limits=cardinality_limits,
            metric_producers=metric_producers,
        )
        self._lock = RLock()
        self._metrics_data: MetricsData | None = None

    def get_metrics_data(
        self,
    ) -> MetricsData | None:
        """Reads and returns current metrics from the SDK

        Returns:
            The batch just collected, or ``None`` when it yielded nothing,
            which covers a reader not registered on a ``MeterProvider``.
        """
        with self._lock:
            self.collect()
            metrics_data = self._metrics_data
            self._metrics_data = None
        return metrics_data

    def _receive_metrics(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        with self._lock:
            self._metrics_data = metrics_data

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Do nothing.

        Args:
            timeout_millis: Ignored.
            **kwargs: Ignored.
        """


class PeriodicExportingMetricReader(MetricReader):
    """`PeriodicExportingMetricReader` is an implementation of `MetricReader`
    that collects metrics based on a user-configurable time interval, and passes the
    metrics to the configured exporter. If the time interval is set to `math.inf`, the
    reader will not invoke periodic collection.

    The configured exporter's :py:meth:`~MetricExporter.export` method will not be called
    concurrently.

    Args:
        exporter: Where each collected batch is sent. Its preferred
            temporality and preferred aggregation become this reader's.
        export_interval_millis: How long to wait between cycles, in
            milliseconds. ``None`` reads ``OTEL_METRIC_EXPORT_INTERVAL`` and
            falls back to 60000 when that variable is unset or unparsable.
            ``math.inf`` starts no thread at all, which leaves
            ``force_flush`` as the only thing that collects, since
            ``shutdown`` collects nothing of its own.
        export_timeout_millis: The budget for one scheduled collection and its
            export, in milliseconds. ``None`` reads
            ``OTEL_METRIC_EXPORT_TIMEOUT`` and falls back to 30000 when that
            variable is unset or unparsable. A collection that exceeds it is
            abandoned with a warning. It bounds only the collections the
            interval triggers: the one final collection the thread runs after
            ``shutdown`` is given ``export_interval_millis`` instead.
        cardinality_limits: The attribute set limit per instrument class, as
            on ``MetricReader``.
        metric_producers: Producers whose metrics are collected together with
            the SDK's own on every cycle.
    """

    def __init__(
        self,
        exporter: MetricExporter,
        export_interval_millis: float | None = None,
        export_timeout_millis: float | None = None,
        cardinality_limits: CardinalityLimits | None = None,
        *,
        metric_producers: Sequence[MetricProducer] = (),
    ) -> None:
        # PeriodicExportingMetricReader defers to exporter for configuration
        super().__init__(
            preferred_temporality=exporter._preferred_temporality,
            preferred_aggregation=exporter._preferred_aggregation,
            cardinality_limits=cardinality_limits,
            metric_producers=metric_producers,
            otel_component_type=OtelComponentTypeValues.PERIODIC_METRIC_READER,
        )

        # This lock is held whenever calling self._exporter.export() to prevent concurrent
        # execution of MetricExporter.export()
        # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exportbatch
        self._export_lock = Lock()

        self._exporter = exporter
        if export_interval_millis is None:
            try:
                export_interval_millis = float(environ.get(OTEL_METRIC_EXPORT_INTERVAL, 60000))
            except ValueError:
                _logger.warning("Found invalid value for export interval, using default")
                export_interval_millis = 60000
        if export_timeout_millis is None:
            try:
                export_timeout_millis = float(environ.get(OTEL_METRIC_EXPORT_TIMEOUT, 30000))
            except ValueError:
                _logger.warning("Found invalid value for export timeout, using default")
                export_timeout_millis = 30000
        self._export_interval_millis = export_interval_millis
        self._export_timeout_millis = export_timeout_millis
        self._shutdown = False
        self._shutdown_event = Event()
        self._shutdown_once = Once()
        self._daemon_thread = None
        if self._export_interval_millis <= 0:
            raise ValueError(
                f"interval value {self._export_interval_millis} is invalid and needs to be larger than zero."
            )
        if self._export_timeout_millis <= 0:
            raise ValueError(
                f"timeout value {self._export_timeout_millis} is invalid and needs to be larger than zero."
            )

        if self._export_interval_millis < math.inf:
            self._daemon_thread = Thread(
                name="OtelPeriodicExportingMetricReader",
                target=self._ticker,
                daemon=True,
            )
            self._daemon_thread.start()
            if hasattr(os, "register_at_fork"):
                weak_at_fork = weakref.WeakMethod(self._at_fork_reinit)

                def _after_in_child() -> None:
                    """Restart the exporting thread in a forked child.

                    The reader is held weakly, so a reader collected before
                    the fork leaves this doing nothing rather than keeping the
                    reader alive for the life of the process.
                    """
                    if at_fork := weak_at_fork():
                        at_fork()

                os.register_at_fork(after_in_child=_after_in_child)

    def _at_fork_reinit(self):
        self._daemon_thread = Thread(
            name="OtelPeriodicExportingMetricReader",
            target=self._ticker,
            daemon=True,
        )
        self._daemon_thread.start()

    def _ticker(self) -> None:
        interval_secs = self._export_interval_millis / 1e3
        while not self._shutdown_event.wait(interval_secs):
            try:
                self.collect(timeout_millis=self._export_timeout_millis)
            except MetricsTimeoutError:
                _logger.warning(
                    "Metric collection timed out. Will try again after %s seconds",
                    interval_secs,
                    exc_info=True,
                )
        # one last collection below before shutting down completely
        try:
            self.collect(timeout_millis=self._export_interval_millis)
        except MetricsTimeoutError:
            _logger.warning(
                "Metric collection timed out.",
                exc_info=True,
            )

    def _receive_metrics(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        # pylint: disable=broad-exception-caught,invalid-name
        try:
            with self._export_lock:
                self._exporter.export(metrics_data, timeout_millis=timeout_millis)
        except Exception:
            _logger.exception("Exception while exporting metrics")
        detach(token)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Stop the exporting thread and shut the exporter down.

        Args:
            timeout_millis: The budget for the wait on the exporting thread,
                in milliseconds, counted from entry.
            **kwargs: Ignored.
        """
        deadline_ns = time_ns() + timeout_millis * 10**6

        def _shutdown():
            """Mark the reader as shut down, under the ``Once`` guard."""
            self._shutdown = True

        did_set = self._shutdown_once.do_once(_shutdown)
        if not did_set:
            _logger.warning("Can't shutdown multiple times")
            return

        self._shutdown_event.set()
        if self._daemon_thread:
            self._daemon_thread.join(timeout=(deadline_ns - time_ns()) / 10**9)
        self._exporter.shutdown(timeout=(deadline_ns - time_ns()) / 10**6)

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Collect and export right now, then flush the exporter.

        Args:
            timeout_millis: Given in full to the collection and then in full
                again to the exporter's flush, so this can take twice as long.

        Returns:
            Always ``True``. What the exporter's flush reported is discarded.
        """
        super().force_flush(timeout_millis=timeout_millis)
        self._exporter.force_flush(timeout_millis=timeout_millis)
        return True
