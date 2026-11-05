# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-lines
"""Implementation of ``MeterProvider`` and ``Meter``.

``MeterProvider`` is the root object of the metrics SDK: it owns the
resource, the views, the exemplar filter and the metric readers, and it
hands out ``Meter`` instances, one per instrumentation scope. ``Meter``
creates instruments and caches them by identity. Both are re-exported from
``opentelemetry.sdk.metrics``, which is where they should be imported from.

Two environment variables are read here, both when a ``MeterProvider`` is
constructed and never again. ``OTEL_SDK_DISABLED`` set to ``true``, compared
after stripping whitespace and lower-casing, makes every ``get_meter`` call
on that provider return a no-op meter. ``OTEL_METRICS_EXEMPLAR_FILTER``
names the exemplar filter, out of ``trace_based``, ``always_on`` and
``always_off``; it is consulted only when the ``exemplar_filter`` argument
was not given, it defaults to ``trace_based``, and any other value raises
``ValueError`` out of the constructor.

This module also holds the meter configuration machinery. A
``_MeterConfig`` carries the settings of one meter, currently just whether
it is enabled. A ``_ProxyMeterConfig`` is the indirection that lets those
settings be replaced after instruments have already been created. A meter
configurator is a callable taking an ``InstrumentationScope`` and returning
a ``_MeterConfig``, which the provider runs once per scope.
"""

import os
import weakref
from atexit import register, unregister
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from logging import getLogger
from os import environ
from threading import Lock
from time import time_ns

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
from opentelemetry.metrics import Counter as APICounter
from opentelemetry.metrics import Histogram as APIHistogram
from opentelemetry.metrics import Meter as APIMeter
from opentelemetry.metrics import MeterProvider as APIMeterProvider
from opentelemetry.metrics import NoOpMeter
from opentelemetry.metrics import ObservableCounter as APIObservableCounter
from opentelemetry.metrics import ObservableGauge as APIObservableGauge
from opentelemetry.metrics import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry.metrics import UpDownCounter as APIUpDownCounter
from opentelemetry.metrics import _Gauge as APIGauge
from opentelemetry.sdk.environment_variables import (
    OTEL_METRICS_EXEMPLAR_FILTER,
    OTEL_SDK_DISABLED,
)
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    ExemplarFilter,
    TraceBasedExemplarFilter,
)
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement_consumer import (
    MeasurementConsumer,
    SynchronousMeasurementConsumer,
)
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.resources import (
    Resource,
    _get_process_dependent_resource,
)
from opentelemetry.sdk.util._configurator import RuleBasedConfigurator
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope,
)
from opentelemetry.util._once import Once
from opentelemetry.util.types import (
    Attributes,
)

_logger = getLogger(__name__)


@dataclass
class _MeterConfig:
    """The settings a ``MeterProvider`` applies to a single meter.

    A meter configurator produces one of these per instrumentation scope,
    and it reaches the meter and its instruments through a
    ``_ProxyMeterConfig``.

    Args:
        is_enabled: Whether the meter records anything. When it is ``False``
            the synchronous instruments of the meter discard every
            measurement and the asynchronous ones report nothing, while
            creating instruments still succeeds and still returns real
            instruments.
    """

    is_enabled: bool = True

    @classmethod
    def default(cls) -> "_MeterConfig":
        """Build the configuration a meter gets when nothing else applies.

        Returns:
            A new instance with ``is_enabled`` set to ``True``. A separate
            object is built on every call, so two meters never share one.
        """
        return _MeterConfig()


class _ProxyMeterConfig:
    """Mutable holder that keeps a meter's configuration replaceable.

    A ``Meter`` and every instrument it creates keep a reference to this
    object rather than to the ``_MeterConfig`` itself, and read through it on
    every measurement. Replacing the configuration with ``update`` therefore
    reaches instruments that already exist, which is what lets
    ``MeterProvider._set_meter_configurator`` take effect on a meter handed
    out earlier.

    Args:
        config: The configuration to hold to begin with.
    """

    def __init__(self, config: _MeterConfig):
        """Store the initial configuration.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._config = config

    @property
    def is_enabled(self) -> bool:
        """Whether the meter this configuration belongs to is enabled.

        Returns:
            The ``is_enabled`` flag of whichever ``_MeterConfig`` is held at
            the moment of the call, so the answer changes as soon as
            ``update`` replaces it.
        """
        return self._config.is_enabled

    def update(self, config: _MeterConfig) -> None:
        """Replace the configuration held.

        The meter and all of its instruments see the change on their next
        measurement, since every one of them reads through this object. The
        replacement is a plain attribute assignment with no lock, so a
        measurement running concurrently may still read the old
        configuration.

        Args:
            config: The configuration to hold from now on.
        """
        self._config = config


class Meter(APIMeter):
    """See `opentelemetry.metrics.Meter`.

    Instruments are cached by identity, which is the instrument name
    stripped and lower-cased, the instrument kind, the unit and the
    description taken together. Asking twice for the same identity returns
    the first instrument, and whatever the second call passed outside those
    four values (callbacks, or a histogram bucket advisory) is discarded.

    Args:
        instrumentation_scope: Identifies the library this meter was created
            for. Every instrument created here carries it, and a ``View``
            matches its ``meter_name``, ``meter_version`` and
            ``meter_schema_url`` criteria against it.
        measurement_consumer: Handed to every instrument created here, and
            told about each asynchronous instrument so that collection can
            call back into it.
        _meter_config: The configuration this meter starts with. ``None``
            means ``_MeterConfig.default()``, which is enabled. It is
            wrapped in a ``_ProxyMeterConfig`` so that
            ``MeterProvider._set_meter_configurator`` can replace it later.
    """

    def __init__(
        self,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        *,
        _meter_config: _MeterConfig | None = None,
    ):
        """Build the meter and its empty instrument cache.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
            schema_url=instrumentation_scope.schema_url,
        )
        self._instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        self._instrument_id_instrument = {}
        self._instrument_registration_lock = Lock()
        self._meter_config = _ProxyMeterConfig(_meter_config or _MeterConfig.default())

    def _is_enabled(self) -> bool:
        """Report whether this meter currently records anything.

        Returns:
            The ``is_enabled`` flag of the configuration held right now. The
            instruments of this meter consult their own copy of the same
            proxy rather than calling this.
        """
        return self._meter_config.is_enabled

    def _set_meter_config(self, meter_config: _MeterConfig) -> None:
        """Replace the configuration of this meter and of its instruments.

        The instruments created by this meter share the one
        ``_ProxyMeterConfig`` updated here, so they pick the new
        configuration up on their next measurement without being visited.

        Args:
            meter_config: The configuration to apply from now on.
        """
        self._meter_config.update(meter_config)

    def create_counter(self, name, unit="", description="") -> APICounter:
        """Create or look up a counter on this meter.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not. It is stripped and
                lower-cased for the identity check and lower-cased on the
                instrument itself.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity, so the
                same name with a different unit is a different instrument.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            A ``Counter``. The same object comes back on every later call
            with the same name, unit and description, with no warning and
            without a second instrument being built.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _Counter, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _Counter(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APICounter.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_up_down_counter(self, name, unit="", description="") -> APIUpDownCounter:
        """Create or look up an up-down counter on this meter.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not. It is stripped and
                lower-cased for the identity check and lower-cased on the
                instrument itself.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            An ``UpDownCounter``. The same object comes back on every later
            call with the same name, unit and description, with no warning
            and without a second instrument being built.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _UpDownCounter, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _UpDownCounter(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIUpDownCounter.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_observable_counter(
        self,
        name,
        callbacks=None,
        unit="",
        description="",
    ) -> APIObservableCounter:
        """Create or look up an observable counter on this meter.

        On first creation the instrument is registered with the measurement
        consumer, which is what makes its callbacks run at collection time.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not.
            callbacks: The callbacks the SDK invokes on every collection,
                each a callable or a generator yielding
                ``opentelemetry.metrics.Observation`` values. ``None``, the
                default, means the instrument reports nothing. Callbacks do
                not take part in the instrument identity, so the ones passed
                to a repeated call are discarded with the rest of that call.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            An ``ObservableCounter``. The same object comes back on every
            later call with the same name, unit and description, keeping the
            callbacks it was first given.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _ObservableCounter, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _ObservableCounter(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    callbacks,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if not status.already_registered:
            self._measurement_consumer.register_asynchronous_instrument(instrument)

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIObservableCounter.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_histogram(
        self,
        name: str,
        unit: str = "",
        description: str = "",
        *,
        explicit_bucket_boundaries_advisory: Sequence[float] | None = None,
    ) -> APIHistogram:
        """Create or look up a histogram on this meter.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.
            explicit_bucket_boundaries_advisory: The bucket boundaries this
                histogram suggests to whatever aggregates it, which a
                ``View`` naming an explicit aggregation overrides. ``None``,
                the default, means no suggestion. Anything that is not a
                sequence of numbers is replaced by ``None`` and logged at
                warning level, so a bad advisory does not stop the
                instrument from being created. The advisory is not part of
                the instrument identity.

        Returns:
            A ``Histogram``. The same object comes back on every later call
            with the same name, unit and description, keeping the advisory
            it was first given. A repeated call whose advisory differs from
            the first logs a warning naming the advisory already in force,
            which makes a histogram the only instrument kind where a
            duplicate registration is reported at all.
        """
        if explicit_bucket_boundaries_advisory is not None:
            invalid_advisory = False
            if isinstance(explicit_bucket_boundaries_advisory, Sequence):
                try:
                    invalid_advisory = not (
                        all(isinstance(e, (float, int)) for e in explicit_bucket_boundaries_advisory)
                    )
                except (KeyError, TypeError):
                    invalid_advisory = True
            else:
                invalid_advisory = True

            if invalid_advisory:
                explicit_bucket_boundaries_advisory = None
                _logger.warning("explicit_bucket_boundaries_advisory must be a sequence of numbers")

        with self._instrument_registration_lock:
            status = self._register_instrument(
                name,
                _Histogram,
                unit,
                description,
                explicit_bucket_boundaries_advisory,
            )
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _Histogram(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    unit,
                    description,
                    explicit_bucket_boundaries_advisory,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIHistogram.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_gauge(self, name, unit="", description="") -> APIGauge:
        """Create or look up a synchronous gauge on this meter.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            A ``Gauge``. The same object comes back on every later call with
            the same name, unit and description, with no warning and without
            a second instrument being built.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _Gauge, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _Gauge(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIGauge.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_observable_gauge(self, name, callbacks=None, unit="", description="") -> APIObservableGauge:
        """Create or look up an observable gauge on this meter.

        On first creation the instrument is registered with the measurement
        consumer, which is what makes its callbacks run at collection time.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not.
            callbacks: The callbacks the SDK invokes on every collection,
                each a callable or a generator yielding
                ``opentelemetry.metrics.Observation`` values. ``None``, the
                default, means the instrument reports nothing. Callbacks do
                not take part in the instrument identity, so the ones passed
                to a repeated call are discarded with the rest of that call.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            An ``ObservableGauge``. The same object comes back on every
            later call with the same name, unit and description, keeping the
            callbacks it was first given.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _ObservableGauge, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _ObservableGauge(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    callbacks,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if not status.already_registered:
            self._measurement_consumer.register_asynchronous_instrument(instrument)

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIObservableGauge.__name__,
                unit,
                description,
                status,
            )
        return instrument

    def create_observable_up_down_counter(
        self, name, callbacks=None, unit="", description=""
    ) -> APIObservableUpDownCounter:
        """Create or look up an observable up-down counter on this meter.

        On first creation the instrument is registered with the measurement
        consumer, which is what makes its callbacks run at collection time.

        Args:
            name: The instrument name. It has to match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, and the constructor of
                the instrument raises if it does not.
            callbacks: The callbacks the SDK invokes on every collection,
                each a callable or a generator yielding
                ``opentelemetry.metrics.Observation`` values. ``None``, the
                default, means the instrument reports nothing. Callbacks do
                not take part in the instrument identity, so the ones passed
                to a repeated call are discarded with the rest of that call.
            unit: The unit of measure, an ASCII string of at most 63
                characters. It is part of the instrument identity.
            description: Free-form text describing the instrument. It is
                part of the instrument identity as well.

        Returns:
            An ``ObservableUpDownCounter``. The same object comes back on
            every later call with the same name, unit and description,
            keeping the callbacks it was first given.
        """
        with self._instrument_registration_lock:
            status = self._register_instrument(name, _ObservableUpDownCounter, unit, description)
            if not status.already_registered:
                self._instrument_id_instrument[status.instrument_id] = _ObservableUpDownCounter(
                    name,
                    self._instrumentation_scope,
                    self._measurement_consumer,
                    callbacks,
                    unit,
                    description,
                    _meter_config=self._meter_config,
                )
            instrument = self._instrument_id_instrument[status.instrument_id]

        if not status.already_registered:
            self._measurement_consumer.register_asynchronous_instrument(instrument)

        if status.conflict:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            self._log_instrument_registration_conflict(
                name,
                APIObservableUpDownCounter.__name__,
                unit,
                description,
                status,
            )
        return instrument


def _get_exemplar_filter(exemplar_filter: str) -> ExemplarFilter:
    """Build the exemplar filter a configuration value names.

    Args:
        exemplar_filter: One of ``"trace_based"``, ``"always_on"`` or
            ``"always_off"``. ``MeterProvider`` passes the value of
            ``OTEL_METRICS_EXEMPLAR_FILTER`` here, unmodified, so the
            comparison is exact and surrounding whitespace or a capital
            letter makes it fail.

    Returns:
        A new instance of the matching filter class.

    Raises:
        ValueError: If ``exemplar_filter`` is none of the three names. The
            message quotes the rejected value.
    """
    if exemplar_filter == "trace_based":
        return TraceBasedExemplarFilter()
    if exemplar_filter == "always_on":
        return AlwaysOnExemplarFilter()
    if exemplar_filter == "always_off":
        return AlwaysOffExemplarFilter()
    msg = f"Unknown exemplar filter '{exemplar_filter}'."
    raise ValueError(msg)


_MeterConfiguratorT = Callable[[InstrumentationScope], _MeterConfig]
_RuleBasedMeterConfigurator = RuleBasedConfigurator[_MeterConfig]


def _default_meter_configurator(
    _meter_scope: InstrumentationScope,
) -> _MeterConfig:
    """Give every meter the default configuration.

    A ``MeterProvider`` built without a ``_meter_configurator`` uses this
    one, which is why a provider enables every meter out of the box.

    Args:
        _meter_scope: The instrumentation scope of the meter being
            configured. It is accepted to satisfy the configurator
            signature and then ignored, since the answer is the same for
            every scope.

    Returns:
        A new ``_MeterConfig`` with ``is_enabled`` set to ``True``.
    """
    return _MeterConfig.default()


def _disable_meter_configurator(
    _meter_scope: InstrumentationScope,
) -> _MeterConfig:
    """Turn off every meter it is applied to.

    Pass this as the ``_meter_configurator`` of a ``MeterProvider``, or hand
    it to ``MeterProvider._set_meter_configurator``, to silence the whole
    provider while instrument creation keeps working.

    Args:
        _meter_scope: The instrumentation scope of the meter being
            configured. It is accepted to satisfy the configurator
            signature and then ignored, since the answer is the same for
            every scope.

    Returns:
        A new ``_MeterConfig`` with ``is_enabled`` set to ``False``.
    """
    return _MeterConfig(is_enabled=False)


class MeterProvider(APIMeterProvider):
    r"""See `opentelemetry.metrics.MeterProvider`.

    Args:
        metric_readers: Register metric readers to collect metrics from the SDK
            on demand. Each :class:`opentelemetry.sdk.metrics.export.MetricReader` is
            completely independent and will collect separate streams of
            metrics. For push-based export, use
            :class:`opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader`.
        resource: The resource representing what the metrics emitted from the SDK pertain to.
            If ``None``, ``Resource.create({})`` is used, which gathers the
            detectors configured through the environment. The resource is
            not frozen: a fork merges the process dependent attributes of
            the child into it.
        exemplar_filter: Decides which measurements are eligible to become
            exemplars. If ``None``, the value of
            ``OTEL_METRICS_EXEMPLAR_FILTER`` is read instead, defaulting to
            ``trace_based``. That is the only moment the variable is
            consulted.
        shutdown_on_exit: If true, registers an `atexit` handler to call
            `MeterProvider.shutdown`
        views: The views to configure the metric output the SDK.
            An instrument that matches no view is aggregated with the
            default aggregation for its kind, and an instrument that matches
            several of them feeds one metric stream per matching view.
        _meter_configurator: Called with one ``InstrumentationScope`` and
            returns the ``_MeterConfig`` for the meter of that scope, which
            is how individual meters are turned off. If ``None``,
            ``_default_meter_configurator`` is used and every meter is
            enabled. Keep it fast: it runs while the meter lock is held.

    .. code-block:: python
        :caption: Push-based export with PeriodicExportingMetricReader

        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )

        reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
        provider = MeterProvider(metric_readers=[reader])

    By default, instruments which do not match any :class:`opentelemetry.sdk.metrics.view.View` (or if no :class:`opentelemetry.sdk.metrics.view.View`\ s
    are provided) will report metrics with the default aggregation for the
    instrument's kind. To disable instruments by default, configure a match-all
    :class:`opentelemetry.sdk.metrics.view.View` with `DropAggregation` and then create :class:`opentelemetry.sdk.metrics.view.View`\ s to re-enable
    individual instruments:

    .. code-block:: python
        :caption: Disable default views

        MeterProvider(
            views=[
                View(instrument_name="*", aggregation=DropAggregation()),
                View(instrument_name="mycounter"),
            ],
            # ...
        )
    """

    _all_metric_readers_lock = Lock()
    _all_metric_readers = weakref.WeakSet()

    def __init__(
        self,
        metric_readers: Sequence["opentelemetry.sdk.metrics.export.MetricReader"] = (),
        resource: Resource | None = None,
        exemplar_filter: ExemplarFilter | None = None,
        shutdown_on_exit: bool = True,
        views: Sequence["opentelemetry.sdk.metrics.view.View"] = (),
        *,
        _meter_configurator: _MeterConfiguratorT | None = None,
    ):
        """Wire the provider to its readers, views and resource.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Each metric reader is claimed here for this provider alone, by way of
        a set shared by every ``MeterProvider`` in the process. The readers
        are given a collect callback and a reference back to this provider
        before the constructor returns, so a reader starts working as soon as
        the provider exists.

        Raises:
            ValueError: If ``exemplar_filter`` was not given and
                ``OTEL_METRICS_EXEMPLAR_FILTER`` holds a name that is not
                one of ``trace_based``, ``always_on`` and ``always_off``.
            Exception: If any reader in ``metric_readers`` is already
                registered with another ``MeterProvider``. The readers
                before it in the sequence have already been claimed by then,
                so they cannot be given to a different provider afterwards.
        """
        self._lock = Lock()
        self._meter_lock = Lock()
        self._atexit_handler = None
        if resource is None:
            resource = Resource.create({})
        self._sdk_config = SdkConfiguration(
            exemplar_filter=(
                exemplar_filter or _get_exemplar_filter(environ.get(OTEL_METRICS_EXEMPLAR_FILTER, "trace_based"))
            ),
            resource=resource,
            views=views,
        )
        self._metric_readers = metric_readers
        self._measurement_consumer = SynchronousMeasurementConsumer(
            sdk_config=self._sdk_config,
            metric_readers=metric_readers,
        )
        disabled = environ.get(OTEL_SDK_DISABLED, "")
        self._disabled = disabled.lower().strip() == "true"

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self._meters: dict[InstrumentationScope, Meter] = {}
        self._shutdown_once = Once()
        self._shutdown = False
        self._meter_configurator = _meter_configurator or _default_meter_configurator

        for metric_reader in self._metric_readers:
            with self._all_metric_readers_lock:
                if metric_reader in self._all_metric_readers:
                    # pylint: disable=broad-exception-raised
                    raise Exception(
                        f"MetricReader {metric_reader} has been registered already in other MeterProvider instance"
                    )

                self._all_metric_readers.add(metric_reader)

            metric_reader._set_collect_callback(self._measurement_consumer.collect)
            metric_reader._set_meter_provider(self)

        if hasattr(os, "register_at_fork"):
            weak_at_fork = weakref.WeakMethod(self._handle_fork)

            def _after_in_child() -> None:
                """Run the provider's fork handler in the freshly forked child.

                ``os.register_at_fork`` keeps a strong reference to whatever is handed
                to it, so this closure holds the provider only weakly. A provider that
                has been garbage collected leaves the weak reference empty and the
                handler does nothing.
                """
                if at_fork := weak_at_fork():
                    at_fork()

            os.register_at_fork(after_in_child=_after_in_child)

    def _handle_fork(self) -> None:
        """Repair this provider inside a process that has just forked.

        ``os.register_at_fork`` runs this in the child, through a weak
        method, so a provider that has been garbage collected is neither
        resurrected nor called. The three locks are replaced because a lock
        another thread held at the instant of the fork would stay held
        forever in the child, which has only the forking thread. Replacing
        ``_all_metric_readers_lock`` assigns to the class of this provider,
        so every provider of that class and of its subclasses gets the new
        lock, while a sibling class keeps the one it inherited.
        The resource is then merged with the process dependent
        attributes of the new process, which is what corrects the recorded
        process id.
        """
        self._lock = Lock()
        self._meter_lock = Lock()
        type(self)._all_metric_readers_lock = Lock()
        self._update_resource(_get_process_dependent_resource())

    def _set_meter_configurator(self, *, meter_configurator: _MeterConfiguratorT):
        """Set a new MeterConfigurator for this MeterProvider.

        Setting a new MeterConfigurator will result in the configurator being called
        for each outstanding Meter and for any newly created meters thereafter.
        Therefore, it is important that the provided function returns quickly.

        The meters are revisited under the meter lock, and each one is
        updated through the ``_ProxyMeterConfig`` it shares with its
        instruments, so instruments created before this call also pick the
        new configuration up.

        Args:
            meter_configurator: Called with one ``InstrumentationScope`` and
                returns the ``_MeterConfig`` for the meter of that scope. An
                exception it raises is logged with a traceback and the
                default configuration is used for that scope instead, so one
                failing scope does not stop the rest from being updated.
        """
        with self._meter_lock:
            self._meter_configurator = meter_configurator
            for instrumentation_scope, meter in self._meters.items():
                # pylint: disable-next=protected-access
                meter._set_meter_config(self._apply_meter_configurator(instrumentation_scope))

    def _update_resource(self, resource: Resource) -> None:
        """Merge further attributes into the resource of this provider.

        On a key both resources carry, the incoming value wins, which is the
        order ``Resource.merge`` defines. The metric readers reach the
        resource through the same ``SdkConfiguration`` object, so the next
        collection sees the merged resource with nothing else being
        notified.

        Args:
            resource: The resource whose attributes are merged in.
        """
        with self._meter_lock:
            self._sdk_config.resource = self._sdk_config.resource.merge(resource)

    def _apply_meter_configurator(self, instrumentation_scope: InstrumentationScope) -> _MeterConfig:
        """Run the meter configurator for one scope, surviving a failure.

        Args:
            instrumentation_scope: The scope of the meter being configured,
                passed to the configurator unchanged.

        Returns:
            Whatever the configurator returned, or ``_MeterConfig.default()``
            when it raised. An exception is logged with a traceback and the
            name of the scope, and is not propagated, so a configurator that
            is broken leaves every meter enabled rather than breaking
            ``get_meter``.
        """
        try:
            return self._meter_configurator(instrumentation_scope)
        # pylint: disable-next=broad-exception-caught
        except Exception:
            _logger.exception(
                "meter configurator failed for scope '%s', using default config",
                instrumentation_scope.name,
            )
            return _MeterConfig.default()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Make every metric reader export what it is holding right now.

        The readers are flushed one after another against a single deadline
        computed when the call starts, so a slow reader leaves less time for
        the ones behind it, and a reader reached after the deadline is
        counted as failed without being flushed. One reader failing does not
        stop the others: every failure is gathered and reported together at
        the end.

        The call may be repeated as often as wanted; nothing guards against
        it, and nothing here checks whether the provider has been shut down.
        Only the readers passed to the constructor are flushed, so a reader
        attached later with ``add_metric_reader`` is skipped.

        Args:
            timeout_millis: Upper bound on the whole operation, in
                milliseconds, shared by all the readers.

        Returns:
            ``True``. There is no return value meaning failure, since a
            failure is raised instead.

        Raises:
            Exception: If any reader raised, or was reached after the
                deadline. The message lists the class name and the ``repr``
                of the error for each one.
        """
        deadline_ns = time_ns() + timeout_millis * 10**6

        metric_reader_error = {}

        for metric_reader in self._metric_readers:
            current_ts = time_ns()
            try:
                if current_ts >= deadline_ns:
                    raise MetricsTimeoutError("Timed out while flushing metric readers")
                metric_reader.force_flush(timeout_millis=(deadline_ns - current_ts) / 10**6)

            # pylint: disable=broad-exception-caught
            except Exception as error:
                metric_reader_error[metric_reader] = error

        if metric_reader_error:
            metric_reader_error_string = "\n".join(
                [
                    f"{metric_reader.__class__.__name__}: {error!r}"
                    for metric_reader, error in metric_reader_error.items()
                ]
            )

            # pylint: disable=broad-exception-raised
            raise Exception(
                "MeterProvider.force_flush failed because the following "
                "metric readers failed during collect:\n"
                f"{metric_reader_error_string}"
            )
        return True

    def shutdown(self, timeout_millis: float = 30_000):
        """Shut the metric readers down and stop handing out real meters.

        The call is idempotent. The second and every later call logs a
        warning, shuts nothing down and returns at once, which is also what
        makes the ``atexit`` handler harmless after a manual shutdown. The
        handler is unregistered here in any case.

        The readers share one deadline computed when the call starts, the
        same way ``force_flush`` works, and a reader reached after it is
        counted as failed without being shut down. One reader failing does
        not stop the others.

        Afterwards ``get_meter`` returns no-op meters. Meters already handed
        out keep working and keep feeding the measurement consumer, and only
        the readers passed to the constructor are shut down, so a reader
        attached later with ``add_metric_reader`` is left running.

        Args:
            timeout_millis: Upper bound on the whole operation, in
                milliseconds, shared by all the readers.

        Raises:
            Exception: If any reader raised, or was reached after the
                deadline. Every reader is attempted first and the failures
                are reported together, listing the class name and the
                ``repr`` of the error for each one.
        """
        deadline_ns = time_ns() + timeout_millis * 10**6

        def _shutdown():
            """Mark the provider as shut down.

            It runs through ``Once``, so only the first ``shutdown`` call on
            this provider reaches it.
            """
            self._shutdown = True

        did_shutdown = self._shutdown_once.do_once(_shutdown)

        if not did_shutdown:
            _logger.warning("shutdown can only be called once")
            return

        metric_reader_error = {}

        for metric_reader in self._metric_readers:
            current_ts = time_ns()
            try:
                if current_ts >= deadline_ns:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Didn't get to execute, deadline already exceeded")
                metric_reader.shutdown(timeout_millis=(deadline_ns - current_ts) / 10**6)

            # pylint: disable=broad-exception-caught
            except Exception as error:
                metric_reader_error[metric_reader] = error

        if self._atexit_handler is not None:
            unregister(self._atexit_handler)
            self._atexit_handler = None

        if metric_reader_error:
            metric_reader_error_string = "\n".join(
                [
                    f"{metric_reader.__class__.__name__}: {error!r}"
                    for metric_reader, error in metric_reader_error.items()
                ]
            )

            # pylint: disable=broad-exception-raised
            raise Exception(
                "MeterProvider.shutdown failed because the following "
                "metric readers failed during shutdown:\n"
                f"{metric_reader_error_string}"
            )

    def get_meter(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> APIMeter:
        """Return the meter of an instrumentation scope, creating it once.

        Meters are cached per scope, and the identity of a scope is its
        name, version, schema URL and attributes taken together, so changing
        any of the four yields a separate meter. The configurator runs once
        per scope, at the moment the meter is created, and not again on a
        later call for the same scope.

        Args:
            name: The name of the instrumenting library. An empty name, or
                ``None``, is refused with a warning and gets a no-op meter.
            version: The version of the instrumenting library. ``None``
                means unversioned, and two versions of one library get two
                meters.
            schema_url: The schema URL of the telemetry this meter emits.
                ``None`` means none was declared.
            attributes: Further attributes describing the scope. ``None``
                means none. They take part in the identity of the scope,
                although not in its hash, so two scopes differing only in
                attributes collide in the cache and are then told apart by
                comparison.

        Returns:
            The ``Meter`` already held for this exact scope, or a new one
            registered under it. A ``NoOpMeter`` comes back instead when
            ``OTEL_SDK_DISABLED`` was true at construction, when this
            provider has been shut down, or when ``name`` is empty. The last
            two are logged at warning level; the disabled case is silent.
        """
        if self._disabled:
            return NoOpMeter(name, version=version, schema_url=schema_url)

        if self._shutdown:
            _logger.warning("A shutdown `MeterProvider` can not provide a `Meter`")
            return NoOpMeter(name, version=version, schema_url=schema_url)

        if not name:
            _logger.warning("Meter name cannot be None or empty.")
            return NoOpMeter(name, version=version, schema_url=schema_url)

        instrumentation_scope = InstrumentationScope(name, version, schema_url, attributes)
        with self._meter_lock:
            if not self._meters.get(instrumentation_scope):
                # FIXME #2558 pass SDKConfig object to meter so that the meter
                # has access to views.
                self._meters[instrumentation_scope] = Meter(
                    instrumentation_scope,
                    self._measurement_consumer,
                    _meter_config=self._apply_meter_configurator(instrumentation_scope),
                )
            return self._meters[instrumentation_scope]

    def add_metric_reader(self, metric_reader: "opentelemetry.sdk.metrics.export.MetricReader") -> None:
        """Attach a metric reader to this provider after construction.

        The reader receives measurements from the next collection onwards.
        Readers are claimed process-wide, so one already attached to any
        ``MeterProvider`` is refused here with a warning and nothing else
        happens; the constructor raises in the same situation.

        A reader attached this way differs in two ways from one passed to
        the constructor. ``MeterProvider.force_flush`` and
        ``MeterProvider.shutdown`` walk only the sequence the constructor
        was given, so neither reaches it. It is also not given a reference
        back to this provider, so it goes on measuring itself into the
        instruments its own constructor built on a ``NoOpMeterProvider``,
        and none of its self-metrics is ever exported.

        Args:
            metric_reader: The reader to attach.
        """
        with self._all_metric_readers_lock:
            if metric_reader in self._all_metric_readers:
                _logger.warning(
                    "MetricReader '%s' has been registered already!",
                    metric_reader,
                )
                return
            self._measurement_consumer.add_metric_reader(metric_reader)
            # pylint: disable-next=protected-access
            metric_reader._set_collect_callback(self._measurement_consumer.collect)
            self._all_metric_readers.add(metric_reader)

    def remove_metric_reader(
        self,
        metric_reader: "opentelemetry.sdk.metrics.export.MetricReader",
    ) -> None:
        """Detach a metric reader from this provider and shut it down.

        The reader stops receiving measurements, its collect callback is
        cleared, and ``shutdown`` is called on it with the reader's own
        default timeout rather than one chosen here, so the reader is spent
        afterwards. It is released from the process-wide claim all the same,
        which means another provider would accept the shut down reader. A
        reader attached to no ``MeterProvider`` at all is refused with a
        warning and nothing happens.

        A reader that was passed to the constructor stays in the sequence
        ``MeterProvider.shutdown`` walks, so shutting the provider down
        later shuts that reader down a second time.

        Args:
            metric_reader: The reader to detach.
        """
        with self._all_metric_readers_lock:
            if metric_reader not in self._all_metric_readers:
                _logger.warning("MetricReader '%s' has not been registered!", metric_reader)
                return
            self._measurement_consumer.remove_metric_reader(metric_reader)
            # pylint: disable-next=protected-access
            metric_reader._set_collect_callback(None)
            metric_reader.shutdown()
            self._all_metric_readers.remove(metric_reader)
