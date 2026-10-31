# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""One metric stream: a view applied to an instrument.

``MetricReaderStorage`` builds a ``_ViewInstrumentMatch`` for every pair of a
view and an instrument the view selects, and one more against a catch-all view
for an instrument no view selects. The object owns the aggregations of that
stream, one per distinct attribute set, and turns them into data points when
the reader collects.

The module also holds ``_hash_attributes``, which turns an attribute set into
the hashable key those aggregations are stored under, and the cardinality
limit constants: ``_DEFAULT_CARDINALITY_LIMIT``, and the attribute set
``otel.metric.overflow=true`` that measurements past the limit are folded
into.
"""

from collections.abc import Mapping, Sequence
from logging import getLogger
from threading import Lock
from time import time_ns
from types import NoneType
from typing import TYPE_CHECKING, cast

from typing_extensions import assert_never

from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    AggregationTemporality,
    DefaultAggregation,
    _Aggregation,
    _SumAggregation,
)
from opentelemetry.sdk.metrics._internal.instrument import _Instrument
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import DataPointT
from opentelemetry.sdk.metrics._internal.view import View
from opentelemetry.util.types import AnyValue, Attributes

_logger = getLogger(__name__)

# Every branch is tagged so that values Python considers equal but the OTel
# data model does not -- True/1/1.0, or a sequence of pairs and the mapping
# it resembles -- produce different aggregation keys.
_HashedAttributes = tuple[
    str,
    str
    | bool
    | int
    | float
    | bytes
    | None
    | tuple["_HashedAttributes", ...]
    | tuple[tuple[str, "_HashedAttributes"], ...],
]


# pylint: disable=inconsistent-return-statements
def _hash_attributes(value: Attributes | AnyValue) -> _HashedAttributes:
    """Turn an attribute set into the key its aggregation is stored under.

    The result is hashable and compares equal only to the result of another
    value the OpenTelemetry data model treats as the same, which plain
    equality on the value would not give: ``True``, ``1`` and ``1.0`` compare
    equal in Python, so each scalar is tagged with the name of its type. A
    sequence and a mapping are tagged in the same way and converted to tuples
    element by element, and the entries of a mapping are sorted by key so that
    two mappings written in a different order give the same key.

    Args:
        value: The whole attribute set, which is a mapping, or one value
            inside it reached by recursion. The caller has already cleaned and
            validated it while building the ``Measurement``.

    Returns:
        A tuple of the type tag and the converted value. Nothing is returned
        for a value of a type outside the OpenTelemetry data model, which a
        validated attribute set cannot hold.
    """
    # Attributes have been cleaned and validated when Measurement was instantiated,
    # so value is guaranteed to match one of the branches below at runtime.
    if isinstance(value, (NoneType, str, int, float, bool, bytes)):
        # bool is a subclass of int and 1 == 1.0, so the value alone is not
        # enough to tell these apart.
        return (type(value).__name__, value)
    if isinstance(value, Sequence):
        return ("sequence", tuple(_hash_attributes(v) for v in value))
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple(
                (k, _hash_attributes(value[k]))
                for k in sorted(
                    value,
                    key=lambda item: item if isinstance(item, str) else str(item),
                )
            ),
        )
    if TYPE_CHECKING:
        assert_never(value)


_DEFAULT_CARDINALITY_LIMIT = 2000

_OVERFLOW_ATTRIBUTES: dict[str, AnyValue] = {"otel.metric.overflow": True}
_OVERFLOW_KEY = _hash_attributes(_OVERFLOW_ATTRIBUTES)


class _ViewInstrumentMatch:
    """The aggregated state of one instrument as seen through one view.

    The name and the description of the stream are fixed here: the view's own
    name and description win where it gives a non-empty one, and the
    instrument's are used otherwise. An empty string therefore counts as
    unset, so a view cannot blank out the description of an instrument. The
    unit is never overridden by a view and is read from the instrument at
    collection time.

    One aggregation is held per distinct attribute set, created on first use
    and keyed by ``_hash_attributes``. The construction also builds a single
    aggregation with no attributes, which is never fed a measurement: it is
    kept so that the storage can read the aggregation class off this object to
    choose the data point type, and so that ``conflicts`` can compare streams
    before either has seen a measurement.

    Args:
        view: The view whose name, description, attribute keys, aggregation
            and exemplar reservoir factory shape the stream. The storage
            passes a catch-all view here for an instrument that no configured
            view selects.
        instrument: The instrument being aggregated. Its name, description and
            unit are the fallbacks for the stream, and its class selects the
            default aggregation.
        instrument_class_aggregation: The reader's mapping of instrument class
            to aggregation, consulted whenever the view asks for
            ``DefaultAggregation``. It is read at every aggregation creation
            rather than copied, so a later change to the mapping is picked up.
        cardinality_limit: How many distinct attribute sets this stream keeps
            before folding the rest into the overflow attribute set.
        reset_on_collect: Whether a delta collection discards the aggregations
            held here. The storage sets this for a synchronous instrument on a
            reader configured for delta temporality, and leaves it false for
            an asynchronous instrument, whose delta conversion needs the
            previous state.
    """

    def __init__(
        self,
        view: View,
        instrument: _Instrument,
        instrument_class_aggregation: dict[type, Aggregation],
        cardinality_limit: int = _DEFAULT_CARDINALITY_LIMIT,
        reset_on_collect: bool = False,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._view = view
        self._cardinality_limit = cardinality_limit
        self._reset_on_collect = reset_on_collect
        # Delta aggregations created after a collection continue from it.
        self._previous_collection_start_nanos: int | None = None
        self._instrument = instrument
        self._attributes_aggregation: dict[_HashedAttributes, _Aggregation] = {}
        self._lock = Lock()
        self._instrument_class_aggregation = instrument_class_aggregation
        self._name = self._view._name or self._instrument.name
        self._description = self._view._description or self._instrument.description
        if not isinstance(self._view._aggregation, DefaultAggregation):
            self._aggregation = self._view._aggregation._create_aggregation(
                self._instrument,
                None,
                self._view._exemplar_reservoir_factory,
                0,
            )
        else:
            self._aggregation = self._instrument_class_aggregation[self._instrument.__class__]._create_aggregation(
                self._instrument,
                None,
                self._view._exemplar_reservoir_factory,
                0,
            )

    def conflicts(self, other: "_ViewInstrumentMatch") -> bool:
        """Report whether the two streams carry the same metric identity.

        The comparison is made on the stream name, the unit of the underlying
        instrument and the class of the aggregation, and it stops at the first
        of those that differs. When both aggregations are sums, the comparison
        continues on the monotonicity of the instrument and on the aggregation
        temporality the instrument was given. The description is not compared,
        and neither are the attribute keys nor the cardinality limit.

        ``MetricReaderStorage`` calls this on every pair of an existing stream
        and a stream it is about to add, and logs a warning when the answer is
        true, since two streams agreeing on all of that cannot be told apart
        once exported.

        Args:
            other: The stream to compare against.

        Returns:
            ``True`` when every compared property agrees, ``False`` as soon as
            one of them differs.
        """
        # pylint: disable=protected-access

        result = (
            self._name == other._name
            and self._instrument.unit == other._instrument.unit
            # The aggregation class is being used here instead of data point
            # type since they are functionally equivalent.
            and self._aggregation.__class__ == other._aggregation.__class__
        )
        if not result:
            return result

        if isinstance(self._aggregation, _SumAggregation):
            # if result is True the two aggregation are of the same type
            self._aggregation = cast(_SumAggregation, self._aggregation)
            other._aggregation = cast(_SumAggregation, other._aggregation)

            result = (
                self._aggregation._instrument_is_monotonic == other._aggregation._instrument_is_monotonic
                and self._aggregation._instrument_aggregation_temporality
                == other._aggregation._instrument_aggregation_temporality
            )

        return result

    # pylint: disable=protected-access
    def consume_measurement(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Fold one measurement into the aggregation for its attribute set.

        The attributes are shallow copied before anything else, so a caller
        that mutates the dict it recorded with afterwards does not change the
        key this measurement was filed under. A mutable value inside that dict
        is still shared, since copying it would cost more than it saves.

        When the view names a set of attribute keys, every attribute whose key
        is outside that set is dropped before the key is computed, which is
        how several attribute sets end up aggregated together. A view naming
        an empty set drops all of them, leaving one aggregation under the
        empty attribute set.

        A measurement whose attribute set is new while the stream already
        holds as many as its cardinality limit allows is aggregated into the
        overflow attribute set instead of its own.

        Args:
            measurement: The measurement to aggregate. Only its attributes are
                read here, the rest is passed on to the aggregation.
            should_sample_exemplar: Whether the aggregation may keep this
                measurement as an exemplar. The measurement consumer has
                already applied the configured exemplar filter to decide this.
        """
        attributes = {}
        if measurement.attributes:
            # Make a shallow copy since the user can mutate the dict after the fact.
            # The user can still modify mutable attribute values (lists/dicts)
            # leading to unexpected behavior, but deep copying is expensive.
            attributes = dict(measurement.attributes)
        if self._view._attribute_keys is not None:
            attributes = {k: v for k, v in attributes.items() if k in self._view._attribute_keys}

        aggr_key = _hash_attributes(attributes)

        if self._reset_on_collect:
            # collect() discards the aggregations, so hold the lock until the
            # measurement is aggregated to not lose it.
            with self._lock:
                self._get_or_create_aggregation(aggr_key, attributes).aggregate(measurement, should_sample_exemplar)
            return

        aggregation = self._attributes_aggregation.get(aggr_key)
        if aggregation is None:
            with self._lock:
                aggregation = self._get_or_create_aggregation(aggr_key, attributes)

        aggregation.aggregate(measurement, should_sample_exemplar)

    def _get_or_create_aggregation(self, aggr_key: _HashedAttributes, attributes: Attributes) -> _Aggregation:
        """Return the aggregation for an attribute set, creating it if needed.

        Must be called with ``self._lock`` held.

        A set that is already known is returned straight away. A set that is
        not costs one slot of the cardinality limit, and once the limit is
        reached every further set is redirected to the single overflow
        aggregation, whose attributes are ``otel.metric.overflow=true``. That
        aggregation takes a slot of its own, so a stream exports at most one
        more point than its limit.

        A newly created aggregation starts at the current time, except on a
        stream that both resets on collection and has already been collected
        at least once, where it starts at the beginning of the current cycle
        so that a delta point for an attribute set first seen mid cycle still
        covers the whole cycle. Only a synchronous instrument collected under
        delta temporality resets, so under the default preferences, which are
        cumulative, the start time is always the current time.

        Args:
            aggr_key: The key of the attribute set, as returned by
                ``_hash_attributes``.
            attributes: The attribute set itself, handed to the new
                aggregation so that it can label its data points. Ignored when
                the limit has been reached, where the overflow attributes are
                used instead.

        Returns:
            The aggregation the measurement should be folded into, which is
            the overflow aggregation when the limit has been reached.
        """
        aggregation = self._attributes_aggregation.get(aggr_key)
        if aggregation is not None:
            return aggregation

        # Overflow is only used once the limit of distinct attribute sets is
        # reached, so the overflow point is exported in addition to them.
        if len(self._attributes_aggregation) >= self._cardinality_limit:
            aggr_key = _OVERFLOW_KEY
            attributes = dict(_OVERFLOW_ATTRIBUTES)
            aggregation = self._attributes_aggregation.get(aggr_key)
            if aggregation is not None:
                return aggregation

        start_time_unix_nano = self._previous_collection_start_nanos or time_ns()
        # pylint: disable=protected-access
        if not isinstance(self._view._aggregation, DefaultAggregation):
            aggregation = self._view._aggregation._create_aggregation(
                self._instrument,
                attributes,
                self._view._exemplar_reservoir_factory,
                start_time_unix_nano,
            )
        else:
            aggregation = self._instrument_class_aggregation[self._instrument.__class__]._create_aggregation(
                self._instrument,
                attributes,
                self._view._exemplar_reservoir_factory,
                start_time_unix_nano,
            )
        self._attributes_aggregation[aggr_key] = aggregation
        return aggregation

    def collect(
        self,
        collection_aggregation_temporality: AggregationTemporality,
        collection_start_nanos: int,
    ) -> Sequence[DataPointT] | None:
        """Turn the aggregations held here into data points.

        When this stream was built with ``reset_on_collect`` and the reader
        asks for delta temporality, every aggregation is dropped as part of
        this call and the next measurement starts a fresh one. An attribute
        set that is not recorded again is therefore reported once and then
        never again, and the cardinality limit is spent per collection cycle
        rather than over the life of the process. In any other case the
        aggregations are kept and the attribute sets accumulate.

        Args:
            collection_aggregation_temporality: The temporality the reader
                asks for, which each aggregation uses to decide whether it
                reports a delta or a running total.
            collection_start_nanos: The time the whole collection started, in
                nanoseconds since the epoch. One value is shared by every
                stream collected in the same pass so that their data points
                carry the same end time.

        Returns:
            One data point per attribute set that produced one, or ``None``
            when none did. An aggregation that has seen no measurement since
            the last collection may produce nothing, so an empty result is not
            the same as having no attribute sets.
        """
        data_points: list[DataPointT] = []
        with self._lock:
            aggregations = self._attributes_aggregation
            if self._reset_on_collect and collection_aggregation_temporality is AggregationTemporality.DELTA:
                self._attributes_aggregation = {}
                self._previous_collection_start_nanos = collection_start_nanos

            for aggregation in aggregations.values():
                data_point = aggregation.collect(collection_aggregation_temporality, collection_start_nanos)
                if data_point is not None:
                    data_points.append(data_point)

        # Returning here None instead of an empty list because the caller
        # does not consume a sequence and to be consistent with the rest of
        # collect methods that also return None.
        return data_points or None
