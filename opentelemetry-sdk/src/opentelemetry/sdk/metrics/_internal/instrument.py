# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-ancestors, unused-import
"""SDK implementations of the metric instruments.

An instrument is the object instrumentation code calls to report a
measurement. The classes here implement the abstract instruments of
``opentelemetry.metrics`` on top of a ``MeasurementConsumer``, which hands
every measurement to the views and metric readers of the ``MeterProvider``
the instrument came from.

Instruments come in two kinds. A synchronous instrument (``Counter``,
``UpDownCounter``, ``Histogram``, ``Gauge``) is called by the application at
the moment the measurement happens, and reports it immediately. An
asynchronous instrument (``ObservableCounter``, ``ObservableUpDownCounter``,
``ObservableGauge``) is given callbacks instead, and the SDK invokes them
during collection.

None of these classes is meant to be constructed directly. Each one rejects
direct instantiation in ``__new__``, and a ``Meter`` creates instruments by
instantiating the ``_``-prefixed subclass of each, declared in this module
for exactly that purpose.

Every constructor validates the instrument name and unit. A name has to
match ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``: it starts with an ASCII letter,
runs to at most 255 characters, and otherwise holds only ASCII letters,
digits, ``-``, ``_``, ``.`` and ``/``. A unit has to be ASCII and at most 63
characters. Either one failing raises a bare ``Exception`` from the
constructor, so an invalid name or unit is a hard failure and not something
the SDK logs and works around. The accepted name is then stored lower-cased,
which is what makes instrument names case-insensitive to a ``View``.

Measurement values are checked at recording time instead, and a value that
fails the check is dropped with a warning on this module's logger rather
than raised.
"""

from __future__ import annotations

import math
from collections.abc import Generator, Iterable, Sequence
from logging import getLogger
from time import time_ns
from typing import (
    TYPE_CHECKING,
    Protocol,
    cast,
    runtime_checkable,
)

# This kind of import is needed to avoid Sphinx errors.
from opentelemetry.context import Context, get_current
from opentelemetry.metrics import Asynchronous, CallbackT, Synchronous
from opentelemetry.metrics import Counter as APICounter
from opentelemetry.metrics import Histogram as APIHistogram
from opentelemetry.metrics import ObservableCounter as APIObservableCounter
from opentelemetry.metrics import ObservableGauge as APIObservableGauge
from opentelemetry.metrics import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry.metrics import UpDownCounter as APIUpDownCounter
from opentelemetry.metrics import _Gauge as APIGauge
from opentelemetry.metrics._internal.instrument import (
    CallbackOptions,
    _MetricsHistogramAdvisory,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.util.types import Attributes

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics._internal import (
        _ProxyMeterConfig,
    )
    from opentelemetry.sdk.metrics._internal.measurement_consumer import (
        MeasurementConsumer,
    )
    from opentelemetry.sdk.util.instrumentation import InstrumentationScope


_logger = getLogger(__name__)


_NAME_ERROR_MESSAGE = "Expected ASCII string of maximum length 255 characters but got {}"
_UNIT_ERROR_MESSAGE = "Expected ASCII string of maximum length 63 characters but got {}"


@runtime_checkable
class _Instrument(Protocol):
    """Structural type for the four attributes view matching reads.

    ``View._match`` and ``_ViewInstrumentMatch`` are handed instruments typed
    as this protocol, so they depend on the attributes they read and not on
    any concrete instrument class. The protocol is ``runtime_checkable``, so
    an ``isinstance`` check against it tests only that the four attributes
    exist.

    ``name`` is the lower-cased instrument name, ``unit`` the unit of
    measure, ``description`` the free-form description (the empty string when
    none was given), and ``instrumentation_scope`` the scope of the ``Meter``
    that created the instrument.
    """

    name: str
    unit: str
    description: str
    instrumentation_scope: InstrumentationScope


class _Synchronous(_Instrument, Synchronous):
    """Base of the instruments the application records into directly.

    The constructor validates the instrument identity and keeps the
    measurement consumer that ``Counter.add``, ``UpDownCounter.add``,
    ``Histogram.record`` and ``Gauge.set`` hand their measurements to.

    Args:
        name: The instrument name. It has to match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, which bounds it to 255
            characters and to ASCII letters, digits, ``-``, ``_``, ``.``
            and ``/``, starting with a letter. It is stored lower-cased, so
            two names differing only in case produce one instrument.
        instrumentation_scope: The scope of the ``Meter`` that created this
            instrument. A ``View`` matches its ``meter_name``,
            ``meter_version`` and ``meter_schema_url`` criteria against it,
            and it identifies the scope the resulting metrics are grouped
            under on export.
        measurement_consumer: Receives every measurement recorded on this
            instrument and passes it to the views and metric readers of the
            ``MeterProvider``.
        unit: The unit of measure, as an ASCII string of at most 63
            characters. ``None`` is accepted and replaced by the empty
            string.
        description: Free-form text saying what the instrument measures.
            ``None`` is accepted and replaced by the empty string.
        _meter_config: The configuration object shared with the creating
            ``Meter``. ``None`` means the instrument is permanently enabled.
            When it is given, the instrument reads it on every recording
            call, so disabling the meter afterwards also silences
            instruments that were created before.
    """

    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        unit: str = "",
        description: str = "",
        *,
        _meter_config: _ProxyMeterConfig | None = None,
    ):
        """Validate the instrument identity and store what recording needs.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            Exception: If ``name`` does not match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, or if ``unit`` is not an
                ASCII string of at most 63 characters. A bare ``Exception``
                is raised in both cases rather than a ``ValueError``, and the
                instrument is not created.
        """
        # pylint: disable=no-member
        result = self._check_name_unit_description(name, unit, description)

        if result["name"] is None:
            # pylint: disable=broad-exception-raised
            raise Exception(_NAME_ERROR_MESSAGE.format(name))

        if result["unit"] is None:
            # pylint: disable=broad-exception-raised
            raise Exception(_UNIT_ERROR_MESSAGE.format(unit))

        name = result["name"]
        unit = result["unit"]
        description = cast(str, result["description"])

        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        self._meter_config = _meter_config
        super().__init__(name, unit=unit, description=description)

    def _is_enabled(self) -> bool:
        """Report whether recording on this instrument is currently on.

        Returns:
            ``True`` when the instrument was built without a meter config, or
            when the shared config reports the meter as enabled. The value is
            read on every call, so a later change to the meter config takes
            effect on the next measurement.
        """
        return self._meter_config is None or self._meter_config.is_enabled


class _Asynchronous(_Instrument, Asynchronous):
    """Base of the instruments the SDK reads from during collection.

    The constructor validates the instrument identity the same way
    ``_Synchronous`` does, then normalizes every callback into a plain
    callable so that ``callback`` can treat them all alike.

    Args:
        name: The instrument name. It has to match
            ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, which bounds it to 255
            characters and to ASCII letters, digits, ``-``, ``_``, ``.``
            and ``/``, starting with a letter. It is stored lower-cased, so
            two names differing only in case produce one instrument.
        instrumentation_scope: The scope of the ``Meter`` that created this
            instrument. A ``View`` matches its ``meter_name``,
            ``meter_version`` and ``meter_schema_url`` criteria against it,
            and it identifies the scope the resulting metrics are grouped
            under on export.
        measurement_consumer: Stored for symmetry with ``_Synchronous``. An
            asynchronous instrument never reads it, because the measurement
            consumer drives the exchange in the other direction: it registers
            the instrument and calls ``callback`` on it at collection time.
        callbacks: The callbacks the SDK invokes on every collection.
            ``None``, which is the default, means the instrument reports
            nothing. Each entry is either a callable taking a
            ``CallbackOptions`` and returning an iterable of
            ``opentelemetry.metrics.Observation``, or a generator that
            yields such an iterable and receives a ``CallbackOptions`` back
            from each ``yield``. A generator is advanced to its first
            ``yield`` here, during construction, and whatever it yields there
            is discarded.
        unit: The unit of measure, as an ASCII string of at most 63
            characters. ``None`` is accepted and replaced by the empty
            string.
        description: Free-form text saying what the instrument measures.
            ``None`` is accepted and replaced by the empty string.
        _meter_config: The configuration object shared with the creating
            ``Meter``. ``None`` means the instrument is permanently enabled.
            When it is given, the instrument reads it at the start of every
            collection, so disabling the meter afterwards also silences
            instruments that were created before.
    """

    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        callbacks: Sequence[CallbackT] | None = None,
        unit: str = "",
        description: str = "",
        *,
        _meter_config: _ProxyMeterConfig | None = None,
    ):
        """Validate the instrument identity and normalize the callbacks.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            Exception: If ``name`` does not match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, or if ``unit`` is not an
                ASCII string of at most 63 characters. A bare ``Exception``
                is raised in both cases rather than a ``ValueError``, and the
                instrument is not created.
            StopIteration: If an entry of ``callbacks`` is a generator that
                is already exhausted, since advancing it to its first
                ``yield`` is what the constructor does with it.
        """
        # pylint: disable=no-member
        result = self._check_name_unit_description(name, unit, description)

        if result["name"] is None:
            # pylint: disable=broad-exception-raised
            raise Exception(_NAME_ERROR_MESSAGE.format(name))

        if result["unit"] is None:
            # pylint: disable=broad-exception-raised
            raise Exception(_UNIT_ERROR_MESSAGE.format(unit))

        name = result["name"]
        unit = result["unit"]
        description = cast(str, result["description"])

        self.name = name.lower()
        self.unit = unit
        self.description = description
        self.instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        self._meter_config = _meter_config
        super().__init__(name, callbacks, unit=unit, description=description)

        self._callbacks: list[CallbackT] = []

        if callbacks is not None:
            for callback in callbacks:
                if isinstance(callback, Generator):
                    # advance generator to it's first yield
                    next(callback)

                    def inner(
                        options: CallbackOptions,
                        callback=callback,
                    ) -> Iterable[Measurement]:
                        """Resume the generator callback and return what it yields next.

                        ``callback`` is bound as a default argument so that each iteration of
                        the enclosing loop captures its own generator rather than the last one.

                        Args:
                            options: The collection options to send into the generator.
                            callback: The generator to resume. Bound at definition time; a
                                caller never passes it.

                        Returns:
                            The measurements the generator yields, or an empty list once the
                            generator is exhausted.
                        """
                        try:
                            return callback.send(options)
                        except StopIteration:
                            return []

                    self._callbacks.append(inner)
                else:
                    self._callbacks.append(callback)

    def _is_enabled(self) -> bool:
        """Report whether this instrument is currently observed.

        Returns:
            ``True`` when the instrument was built without a meter config, or
            when the shared config reports the meter as enabled. ``callback``
            consults this once per collection, so a later change to the meter
            config takes effect on the next collection.
        """
        return self._meter_config is None or self._meter_config.is_enabled

    def callback(self, callback_options: CallbackOptions) -> Iterable[Measurement]:
        """Run the callbacks and convert what they report.

        This is a generator, so the callbacks only run as the caller consumes
        the result. The measurement consumer calls it once per collection.

        A callback that raises is logged with a traceback and abandoned; the
        callbacks after it still run, and the measurements the failing
        callback had already produced are kept. A reported value that is not
        finite (``nan``, ``inf`` or ``-inf``) is logged at warning level and
        skipped, while the rest of the same callback's observations are
        still used. Neither case propagates an exception to the caller.

        Args:
            callback_options: Passed to each callback unchanged. It carries
                the timeout the callback is expected to respect; nothing here
                enforces it.

        Yields:
            One ``Measurement`` per finite observation, timestamped with the
            moment it was converted rather than the moment the callback ran.
            The context of the observation is used when it holds anything. An
            observation carrying ``None``, and one carrying an empty
            ``Context``, both get the context current at the moment of the
            conversion, since the two cases are indistinguishable here.
            Nothing is yielded at all when the meter is disabled.
        """
        if not self._is_enabled():
            return
        for callback in self._callbacks:
            try:
                for api_measurement in callback(callback_options):
                    if not math.isfinite(api_measurement.value):
                        _logger.warning(
                            "Callback returned a non-finite value %s for instrument %s, ignoring measurement.",
                            api_measurement.value,
                            self.name,
                        )
                        continue
                    yield Measurement(
                        api_measurement.value,
                        time_unix_nano=time_ns(),
                        instrument=self,
                        context=api_measurement.context or get_current(),
                        attributes=api_measurement.attributes,
                    )
            except Exception:  # pylint: disable=broad-exception-caught
                _logger.exception("Callback failed for instrument %s.", self.name)


class Counter(_Synchronous, APICounter):
    """Synchronous instrument for a quantity that only ever increases.

    Obtain one from ``Meter.create_counter`` rather than by calling this
    class, which refuses direct instantiation. The constructor parameters are
    documented on ``_Synchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``Counter`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_Counter``.

        Raises:
            TypeError: If ``Counter`` is instantiated directly instead of
                through ``Meter.create_counter``.
        """
        if cls is Counter:
            raise TypeError("Counter must be instantiated via a meter.")
        return super().__new__(cls)

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ):
        """Add a non-negative increment to the counter.

        The measurement is dropped, with a warning naming the instrument, if
        ``amount`` is not finite or is negative. Nothing is raised in either
        case. When the creating meter is disabled the call does nothing at
        all, and the value is not even checked.

        Args:
            amount: How much to add. It has to be finite and non-negative.
            attributes: Attributes to attach to the measurement, which decide
                which time series within the metric stream it lands in.
                ``None`` means no attributes.
            context: The context to associate with the measurement, which is
                what a trace-based exemplar filter inspects. ``None`` means
                the context current at the moment of the call.
        """
        if not self._is_enabled():
            super().add(amount, attributes=attributes, context=context)
            return

        if not math.isfinite(amount):
            _logger.warning(
                "Add amount %s is not finite on Counter %s, ignoring measurement.",
                amount,
                self.name,
            )
            return
        if amount < 0:
            _logger.warning("Add amount must be non-negative on Counter %s.", self.name)
            return
        time_unix_nano = time_ns()
        self._measurement_consumer.consume_measurement(
            Measurement(
                amount,
                time_unix_nano,
                self,
                context or get_current(),
                attributes,
            )
        )


class UpDownCounter(_Synchronous, APIUpDownCounter):
    """Synchronous instrument for a quantity that rises and falls.

    Obtain one from ``Meter.create_up_down_counter`` rather than by calling
    this class, which refuses direct instantiation. The constructor
    parameters are documented on ``_Synchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``UpDownCounter`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_UpDownCounter``.

        Raises:
            TypeError: If ``UpDownCounter`` is instantiated directly instead
                of through ``Meter.create_up_down_counter``.
        """
        if cls is UpDownCounter:
            raise TypeError("UpDownCounter must be instantiated via a meter.")
        return super().__new__(cls)

    def add(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ):
        """Add a signed delta to the counter.

        A negative ``amount`` is accepted here, which is the one thing that
        separates this from ``Counter.add``. A value that is not finite is
        dropped with a warning naming the instrument, and nothing is raised.
        When the creating meter is disabled the call does nothing at all, and
        the value is not even checked.

        Args:
            amount: How much to add. It may be negative, and has to be
                finite.
            attributes: Attributes to attach to the measurement, which decide
                which time series within the metric stream it lands in.
                ``None`` means no attributes.
            context: The context to associate with the measurement, which is
                what a trace-based exemplar filter inspects. ``None`` means
                the context current at the moment of the call.
        """
        if not self._is_enabled():
            super().add(amount, attributes=attributes, context=context)
            return

        if not math.isfinite(amount):
            _logger.warning(
                "Add amount %s is not finite on UpDownCounter %s, ignoring measurement.",
                amount,
                self.name,
            )
            return
        time_unix_nano = time_ns()
        self._measurement_consumer.consume_measurement(
            Measurement(
                amount,
                time_unix_nano,
                self,
                context or get_current(),
                attributes,
            )
        )


class ObservableCounter(_Asynchronous, APIObservableCounter):
    """Asynchronous instrument whose callbacks report a running total.

    The callbacks report the cumulative value reached so far, not the
    increment since the previous collection, and the SDK derives the
    increment from consecutive observations. Obtain one from
    ``Meter.create_observable_counter`` rather than by calling this class,
    which refuses direct instantiation. The constructor parameters are
    documented on ``_Asynchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``ObservableCounter`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_ObservableCounter``.

        Raises:
            TypeError: If ``ObservableCounter`` is instantiated directly
                instead of through ``Meter.create_observable_counter``.
        """
        if cls is ObservableCounter:
            raise TypeError("ObservableCounter must be instantiated via a meter.")
        return super().__new__(cls)


class ObservableUpDownCounter(_Asynchronous, APIObservableUpDownCounter):
    """Asynchronous instrument whose callbacks report an additive total.

    The callbacks report the current value, which may be lower than the one
    reported at the previous collection. Obtain one from
    ``Meter.create_observable_up_down_counter`` rather than by calling this
    class, which refuses direct instantiation. The constructor parameters are
    documented on ``_Asynchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``ObservableUpDownCounter`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_ObservableUpDownCounter``.

        Raises:
            TypeError: If ``ObservableUpDownCounter`` is instantiated
                directly instead of through
                ``Meter.create_observable_up_down_counter``.
        """
        if cls is ObservableUpDownCounter:
            raise TypeError("ObservableUpDownCounter must be instantiated via a meter.")
        return super().__new__(cls)


class Histogram(_Synchronous, APIHistogram):
    """Synchronous instrument for the distribution of recorded values.

    This is the one instrument with a constructor of its own, because it
    carries an advisory about the bucket boundaries it would prefer. The
    advisory is a hint: a ``View`` that names an explicit aggregation
    overrides it.

    Obtain one from ``Meter.create_histogram`` rather than by calling this
    class, which refuses direct instantiation.

    Args:
        name: The instrument name, validated and lower-cased exactly as
            ``_Synchronous`` describes.
        instrumentation_scope: The scope of the ``Meter`` that created this
            instrument.
        measurement_consumer: Receives every recorded measurement and passes
            it to the views and metric readers of the ``MeterProvider``.
        unit: The unit of measure, as an ASCII string of at most 63
            characters.
        description: Free-form text saying what the instrument measures.
        explicit_bucket_boundaries_advisory: The bucket boundaries this
            histogram suggests to whatever aggregates it. ``None``, the
            default, means no suggestion, and the aggregation then picks its
            own boundaries. ``Meter.create_histogram`` replaces a value that
            is not a sequence of numbers with ``None`` and logs a warning, so
            an instrument built through a meter never holds an invalid
            advisory; constructing this class directly performs no such
            check.
        _meter_config: The configuration object shared with the creating
            ``Meter``. ``None`` means the instrument is permanently enabled.
    """

    def __init__(
        self,
        name: str,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
        unit: str = "",
        description: str = "",
        explicit_bucket_boundaries_advisory: Sequence[float] | None = None,
        *,
        _meter_config: _ProxyMeterConfig | None = None,
    ):
        """Build the instrument and wrap its bucket boundary advisory.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            Exception: If ``name`` does not match
                ``[a-zA-Z][-_./a-zA-Z0-9]{0,254}``, or if ``unit`` is not an
                ASCII string of at most 63 characters.
        """
        super().__init__(
            name,
            unit=unit,
            description=description,
            instrumentation_scope=instrumentation_scope,
            measurement_consumer=measurement_consumer,
            _meter_config=_meter_config,
        )
        self._advisory = _MetricsHistogramAdvisory(explicit_bucket_boundaries=explicit_bucket_boundaries_advisory)

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``Histogram`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_Histogram``.

        Raises:
            TypeError: If ``Histogram`` is instantiated directly instead of
                through ``Meter.create_histogram``.
        """
        if cls is Histogram:
            raise TypeError("Histogram must be instantiated via a meter.")
        return super().__new__(cls)

    def record(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ):
        """Record one value into the distribution.

        The measurement is dropped, with a warning naming the instrument, if
        ``amount`` is not finite or is negative. Nothing is raised in either
        case. When the creating meter is disabled the call does nothing at
        all, and the value is not even checked.

        Args:
            amount: The value to record. It has to be finite and
                non-negative.
            attributes: Attributes to attach to the measurement, which decide
                which time series within the metric stream it lands in.
                ``None`` means no attributes.
            context: The context to associate with the measurement, which is
                what a trace-based exemplar filter inspects. ``None`` means
                the context current at the moment of the call.
        """
        if not self._is_enabled():
            super().record(amount, attributes=attributes, context=context)
            return

        if not math.isfinite(amount):
            _logger.warning(
                "Record amount %s is not finite on Histogram %s, ignoring measurement.",
                amount,
                self.name,
            )
            return
        if amount < 0:
            _logger.warning(
                "Record amount must be non-negative on Histogram %s.",
                self.name,
            )
            return
        time_unix_nano = time_ns()
        self._measurement_consumer.consume_measurement(
            Measurement(
                amount,
                time_unix_nano,
                self,
                context or get_current(),
                attributes,
            )
        )


class Gauge(_Synchronous, APIGauge):
    """Synchronous instrument for the latest value of something sampled.

    Only the last value recorded before a collection is reported; earlier
    ones in the same collection cycle are replaced. Obtain one from
    ``Meter.create_gauge`` rather than by calling this class, which refuses
    direct instantiation. The constructor parameters are documented on
    ``_Synchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``Gauge`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_Gauge``.

        Raises:
            TypeError: If ``Gauge`` is instantiated directly instead of
                through ``Meter.create_gauge``.
        """
        if cls is Gauge:
            raise TypeError("Gauge must be instantiated via a meter.")
        return super().__new__(cls)

    def set(
        self,
        amount: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ):
        """Record the current value of the gauge.

        A negative ``amount`` is fine. A value that is not finite is dropped
        with a warning naming the instrument, and nothing is raised, which
        leaves the previously recorded value in place. When the creating
        meter is disabled the call does nothing at all, and the value is not
        even checked.

        Args:
            amount: The value the gauge now holds. It has to be finite.
            attributes: Attributes to attach to the measurement, which decide
                which time series within the metric stream it lands in.
                ``None`` means no attributes.
            context: The context to associate with the measurement, which is
                what a trace-based exemplar filter inspects. ``None`` means
                the context current at the moment of the call.
        """
        if not self._is_enabled():
            super().set(amount, attributes=attributes, context=context)
            return

        if not math.isfinite(amount):
            _logger.warning(
                "Set amount %s is not finite on Gauge %s, ignoring measurement.",
                amount,
                self.name,
            )
            return
        time_unix_nano = time_ns()
        self._measurement_consumer.consume_measurement(
            Measurement(
                amount,
                time_unix_nano,
                self,
                context or get_current(),
                attributes,
            )
        )


class ObservableGauge(_Asynchronous, APIObservableGauge):
    """Asynchronous instrument whose callbacks report a current value.

    Each observation stands on its own and is not combined with the one
    before it. Obtain one from ``Meter.create_observable_gauge`` rather than
    by calling this class, which refuses direct instantiation. The
    constructor parameters are documented on ``_Asynchronous``.
    """

    def __new__(cls, *args, **kwargs):
        """Refuse construction of ``ObservableGauge`` itself.

        Args:
            *args: Forwarded to ``object.__new__`` by way of ``super``, which
                ignores them.
            **kwargs: Ignored, for the same reason.

        Returns:
            A new instance, but only when ``cls`` is a subclass such as
            ``_ObservableGauge``.

        Raises:
            TypeError: If ``ObservableGauge`` is instantiated directly
                instead of through ``Meter.create_observable_gauge``.
        """
        if cls is ObservableGauge:
            raise TypeError("ObservableGauge must be instantiated via a meter.")
        return super().__new__(cls)


# Below classes exist to prevent the direct instantiation
class _Counter(Counter):
    """The concrete counter a ``Meter`` instantiates.

    It adds nothing to ``Counter``. It exists so that the ``__new__`` guard
    on ``Counter`` can reject every other caller while this subclass passes.
    """


class _UpDownCounter(UpDownCounter):
    """The concrete up-down counter a ``Meter`` instantiates.

    It adds nothing to ``UpDownCounter``. It exists so that the ``__new__``
    guard on ``UpDownCounter`` can reject every other caller while this
    subclass passes.
    """


class _ObservableCounter(ObservableCounter):
    """The concrete observable counter a ``Meter`` instantiates.

    It adds nothing to ``ObservableCounter``. It exists so that the
    ``__new__`` guard on ``ObservableCounter`` can reject every other caller
    while this subclass passes.
    """


class _ObservableUpDownCounter(ObservableUpDownCounter):
    """The concrete observable up-down counter a ``Meter`` instantiates.

    It adds nothing to ``ObservableUpDownCounter``. It exists so that the
    ``__new__`` guard on ``ObservableUpDownCounter`` can reject every other
    caller while this subclass passes.
    """


class _Histogram(Histogram):
    """The concrete histogram a ``Meter`` instantiates.

    It adds nothing to ``Histogram``. It exists so that the ``__new__``
    guard on ``Histogram`` can reject every other caller while this subclass
    passes.
    """


class _Gauge(Gauge):
    """The concrete gauge a ``Meter`` instantiates.

    It adds nothing to ``Gauge``. It exists so that the ``__new__`` guard on
    ``Gauge`` can reject every other caller while this subclass passes.
    """


class _ObservableGauge(ObservableGauge):
    """The concrete observable gauge a ``Meter`` instantiates.

    It adds nothing to ``ObservableGauge``. It exists so that the
    ``__new__`` guard on ``ObservableGauge`` can reject every other caller
    while this subclass passes.
    """
