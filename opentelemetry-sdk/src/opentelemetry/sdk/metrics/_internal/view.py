# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from collections.abc import Callable
from fnmatch import fnmatchcase
from logging import getLogger

from opentelemetry.metrics import Instrument
from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    DefaultAggregation,
    _Aggregation,
    _ExplicitBucketHistogramAggregation,
    _ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    ExemplarReservoirBuilder,
    SimpleFixedSizeExemplarReservoir,
)
from opentelemetry.sdk.metrics._internal.instrument import _Instrument

_logger = getLogger(__name__)


def _default_reservoir_factory(
    aggregation_type: type[_Aggregation],
) -> ExemplarReservoirBuilder:
    """Default reservoir factory per aggregation."""
    if issubclass(aggregation_type, _ExplicitBucketHistogramAggregation):
        return AlignedHistogramBucketExemplarReservoir
    if issubclass(aggregation_type, _ExponentialBucketHistogramAggregation):
        return SimpleFixedSizeExemplarReservoir
    return SimpleFixedSizeExemplarReservoir


class View:
    """
    A `View` configuration parameters can be used for the following
    purposes:

    1. Match instruments: When an instrument matches a view, measurements
       received by that instrument will be processed.
    2. Customize metric streams: A metric stream is identified by a match
       between a view and an instrument and a set of attributes. The metric
       stream can be customized by certain attributes of the corresponding view.

    The attributes documented next serve one of the previous two purposes.

    Args:
        instrument_type: This is an instrument matching attribute: the class the
            instrument must be to match the view. The test is
            ``isinstance``, so a base class such as ``Counter`` also selects
            the ``_Counter`` a meter actually creates. ``None`` means the
            class of the instrument is not considered.

        instrument_name: This is an instrument matching attribute: the name the
            instrument must have to match the view. Wild card characters are supported. Wild
            card characters should not be used with this attribute if the view has also a
            ``name`` defined. Matching goes through ``fnmatch.fnmatchcase``,
            so ``*`` stands for any run of characters, ``?`` for exactly one,
            and ``[seq]`` for one character out of ``seq`` (with ``[!seq]``
            for one character outside it). The comparison is
            case-insensitive, because the SDK stores instrument names
            lower-cased and this pattern is lower-cased before it is applied.
            ``None`` means the name of the instrument is not considered.

        meter_name: This is an instrument matching attribute: the name the
            instrument meter must have to match the view. This one is
            compared for equality, with no wild card handling and no case
            folding. ``None`` means the name of the meter is not considered.

        meter_version: This is an instrument matching attribute: the version
            the instrument meter must have to match the view. Compared for
            equality, like ``meter_name``. ``None`` means the version of the
            meter is not considered, so it cannot be used to select only the
            meters that were created without a version.

        meter_schema_url: This is an instrument matching attribute: the schema
            URL the instrument meter must have to match the view. Compared
            for equality, like ``meter_name``. ``None`` means the schema URL
            of the meter is not considered.

        name: This is a metric stream customizing attribute: the name of the
            metric stream. If `None`, the name of the instrument will be used.
            When `name` is specified, `instrument_name` must also be specified
            and cannot contain wildcard characters.

        description: This is a metric stream customizing attribute: the
            description of the metric stream. If `None`, the description of the instrument will
            be used.

        attribute_keys: This is a metric stream customizing attribute: this is
            a set of attribute keys. If not `None` then only the measurement attributes that
            are in ``attribute_keys`` will be used to identify the metric stream.
            Keys outside the set are dropped from the measurement, which
            merges the time series that differed only in those keys and is
            the usual way of cutting cardinality. An empty set keeps no key
            at all, so every measurement collapses into a single point with
            no attributes. ``None`` keeps every attribute the measurement
            carries.

        aggregation: This is a metric stream customizing attribute: the
            aggregation instance to use when data is aggregated for the
            corresponding metrics stream. If `None` an instance of
            `DefaultAggregation` will be used. A ``DropAggregation`` here
            discards the stream entirely, which is how an instrument is
            turned off through a view.

        exemplar_reservoir_factory: This is a metric stream customizing attribute:
            the exemplar reservoir factory. It is called with the aggregation
            class of the stream and returns the reservoir class to build for
            it. ``None`` selects ``_default_reservoir_factory``, which gives
            an explicit bucket histogram one exemplar per bucket and
            everything else a fixed size reservoir.

        instrument_unit: This is an instrument matching attribute: the unit the
            instrument must have to match the view. Matching goes through
            ``fnmatch.fnmatchcase``, so the same wild cards as
            ``instrument_name`` apply, but the comparison is case-sensitive
            because units are. ``None`` means the unit of the instrument is
            not considered.

        aggregation_cardinality_limit: This is a metric stream customizing
            attribute: the maximum number of distinct attribute sets the
            stream holds at once. Measurements with further attribute sets are
            aggregated into one additional point identified by the attribute
            ``otel.metric.overflow=true``. The attribute sets are released on
            collection only for a synchronous instrument collected with delta
            temporality, so under the default cumulative preference the limit
            is spent over the life of the stream rather than per collection
            cycle. If `None` the cardinality limit of the metric reader is
            used, which defaults to 2000. Must be a positive integer.

    This class is not intended to be subclassed by the user.
    """

    _default_aggregation = DefaultAggregation()

    def __init__(
        self,
        instrument_type: type[Instrument] | None = None,
        instrument_name: str | None = None,
        meter_name: str | None = None,
        meter_version: str | None = None,
        meter_schema_url: str | None = None,
        name: str | None = None,
        description: str | None = None,
        attribute_keys: set[str] | None = None,
        aggregation: Aggregation | None = None,
        exemplar_reservoir_factory: Callable[[type[_Aggregation]], ExemplarReservoirBuilder] | None = None,
        instrument_unit: str | None = None,
        aggregation_cardinality_limit: int | None = None,
    ):
        if aggregation_cardinality_limit is not None and (
            isinstance(aggregation_cardinality_limit, bool)
            or not isinstance(aggregation_cardinality_limit, int)
            or aggregation_cardinality_limit < 1
        ):
            raise ValueError(
                f"aggregation_cardinality_limit must be a positive integer, got {aggregation_cardinality_limit!r}"
            )

        if (
            instrument_type
            is instrument_name
            is instrument_unit
            is meter_name
            is meter_version
            is meter_schema_url
            is None
        ):
            # pylint: disable=broad-exception-raised
            raise Exception(f"Some instrument selection criteria must be provided for View {name}")

        if name is not None:
            if instrument_name is None:
                # pylint: disable=broad-exception-raised
                raise Exception(
                    f"View {name} specifies a name but no instrument_name, which may select multiple instruments"
                )
            if any(c in instrument_name for c in "*?["):
                # pylint: disable=broad-exception-raised
                raise Exception(f"View {name} declared with wildcard characters in instrument_name")

        # _name, _description, _aggregation, _exemplar_reservoir_factory,
        # _attribute_keys and _aggregation_cardinality_limit will be accessed
        # when instantiating a _ViewInstrumentMatch.
        self._name = name
        self._instrument_type = instrument_type
        self._instrument_name = instrument_name
        self._instrument_unit = instrument_unit
        self._meter_name = meter_name
        self._meter_version = meter_version
        self._meter_schema_url = meter_schema_url

        self._description = description
        self._attribute_keys = attribute_keys
        self._aggregation = aggregation or self._default_aggregation
        self._exemplar_reservoir_factory = exemplar_reservoir_factory or _default_reservoir_factory
        self._aggregation_cardinality_limit = aggregation_cardinality_limit

    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    def _match(self, instrument: _Instrument) -> bool:
        if self._instrument_type is not None:
            if not isinstance(instrument, self._instrument_type):
                return False

        if self._instrument_name is not None:
            # Instrument names are treated case-insensitively and are stored
            # lower-cased by the SDK, so the pattern is lower-cased to match.
            # fnmatchcase is used instead of fnmatch so it does not rely
            # on the host platform's filename case sensitivity (normcase).
            if not fnmatchcase(instrument.name, self._instrument_name.lower()):
                return False

        if self._instrument_unit is not None:
            # Unit comparison is performed in an exact case-sensitive manner.
            if instrument.unit != self._instrument_unit:
                return False

        if self._meter_name is not None:
            if instrument.instrumentation_scope.name != self._meter_name:
                return False

        if self._meter_version is not None:
            if instrument.instrumentation_scope.version != self._meter_version:
                return False

        if self._meter_schema_url is not None:
            if instrument.instrumentation_scope.schema_url != self._meter_schema_url:
                return False

        return True
