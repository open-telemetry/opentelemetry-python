# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The per-reader half of the SDK's metric state.

Each metric reader registered on a ``MeterProvider`` gets one
``MetricReaderStorage``, since two readers may ask for different temporalities
and different aggregations of the very same instrument. The storage decides
which views apply to an instrument the first time a measurement from it
arrives, keeps a ``_ViewInstrumentMatch`` per applicable view, and assembles
the ``MetricsData`` the reader exports.

The module also holds ``_DEFAULT_VIEW``, the view used for an instrument that
no configured view selects.
"""

from logging import getLogger
from threading import RLock
from time import time_ns

from opentelemetry.metrics import (
    Asynchronous,
    Counter,
    ObservableCounter,
)
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _DEFAULT_CARDINALITY_LIMIT,
    _ViewInstrumentMatch,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    AggregationTemporality,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    _DropAggregation,
    _ExplicitBucketHistogramAggregation,
    _ExponentialBucketHistogramAggregation,
    _LastValueAggregation,
    _SumAggregation,
)
from opentelemetry.sdk.metrics._internal.instrument import (
    _Asynchronous,
    _Instrument,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.point import (
    ExponentialHistogram,
    Gauge,
    Histogram,
    Metric,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.metrics._internal.view import View
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

_logger = getLogger(__name__)

_DEFAULT_VIEW = View(instrument_name="")


class MetricReaderStorage:
    """The SDK's storage for a given reader

    The three mappings passed here come from the reader and are consulted by
    instrument class, so one reader can collect a counter as a delta while
    another collects the same counter cumulatively. The mappings are kept by
    reference rather than copied.

    Args:
        sdk_config: The provider's configuration, read for the views to match
            instruments against and for the resource stamped on the collected
            ``MetricsData``.
        instrument_class_temporality: Maps each SDK instrument class to the
            temporality the reader wants for it. An instrument whose class is
            absent raises ``KeyError`` when it is first collected, and the
            readers that ship with the SDK fill in every class.
        instrument_class_aggregation: Maps each SDK instrument class to the
            aggregation to use when the matched view asks for the default one.
        instrument_class_cardinality_limit: Maps each SDK instrument class to
            the number of distinct attribute sets a stream of that class holds
            at once. They are released on collection only for a synchronous
            instrument collected with delta temporality, so under the default
            cumulative preference the limit is spent over the life of the
            stream. A class that is absent, and the value ``None`` for the
            whole mapping, fall back to 2000. A limit set on the matched view
            wins over this.
    """

    def __init__(
        self,
        sdk_config: SdkConfiguration,
        instrument_class_temporality: dict[type, AggregationTemporality],
        instrument_class_aggregation: dict[type, Aggregation],
        instrument_class_cardinality_limit: dict[type, int] | None = None,
    ) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._lock = RLock()
        self._sdk_config = sdk_config
        self._instrument_view_instrument_matches: dict[_Instrument, list[_ViewInstrumentMatch]] = {}
        self._instrument_class_temporality = instrument_class_temporality
        self._instrument_class_aggregation = instrument_class_aggregation
        self._instrument_class_cardinality_limit = instrument_class_cardinality_limit or {}

    def _new_view_instrument_match(self, view: View, instrument: _Instrument) -> _ViewInstrumentMatch:
        """Build the stream for one pair of a view and an instrument.

        The cardinality limit is resolved here: the limit set on the view wins,
        then the reader's limit for the instrument's class, then 2000.

        Args:
            view: The view to apply. ``_DEFAULT_VIEW`` is passed for an
                instrument that no configured view selects.
            instrument: The instrument the stream reads from.

        Returns:
            A stream that discards its aggregations on every delta collection
            when the instrument is synchronous and the reader asks for delta
            temporality, and keeps them otherwise. An asynchronous instrument
            always keeps them, because the running total it reports is what
            the delta is computed from.
        """
        # pylint: disable=protected-access
        cardinality_limit = view._aggregation_cardinality_limit
        if cardinality_limit is None:
            cardinality_limit = self._instrument_class_cardinality_limit.get(
                instrument.__class__, _DEFAULT_CARDINALITY_LIMIT
            )

        # Idle attribute sets of synchronous instruments are only released on
        # delta collection, so that the limit applies per collection cycle.
        # Asynchronous instruments keep their state, which delta conversion
        # relies on.
        reset_on_collect = self._instrument_class_temporality[
            instrument.__class__
        ] is AggregationTemporality.DELTA and not isinstance(instrument, _Asynchronous)

        return _ViewInstrumentMatch(
            view=view,
            instrument=instrument,
            instrument_class_aggregation=self._instrument_class_aggregation,
            cardinality_limit=cardinality_limit,
            reset_on_collect=reset_on_collect,
        )

    def _get_or_init_view_instrument_match(self, instrument: _Instrument) -> list[_ViewInstrumentMatch]:
        """Return the streams of an instrument, matching views on first sight.

        The matching runs once per instrument and the result is then fixed, so
        a view added to the provider afterwards has no effect on an instrument
        that has already recorded something. The lookup outside the lock is
        the common case; the lock is taken only to decide the matching, and
        the check is repeated inside it because another thread may have
        decided it in the meantime.

        Args:
            instrument: The instrument a measurement just arrived from.

        Returns:
            One stream per view that selects the instrument and is compatible
            with it, in the order the views were configured. A single stream
            built from ``_DEFAULT_VIEW`` when no view selects it, so an
            instrument is never left without one. The same list object is
            returned on every later call.
        """
        # Optimistically get the relevant views for the given instrument. Once set for a given
        # instrument, the mapping will never change

        if instrument in self._instrument_view_instrument_matches:
            return self._instrument_view_instrument_matches[instrument]

        with self._lock:
            # double check if it was set before we held the lock
            if instrument in self._instrument_view_instrument_matches:
                return self._instrument_view_instrument_matches[instrument]

            # not present, hold the lock and add a new mapping
            view_instrument_matches = []

            self._handle_view_instrument_match(instrument, view_instrument_matches)

            # if no view targeted the instrument, use the default
            if not view_instrument_matches:
                view_instrument_matches.append(self._new_view_instrument_match(_DEFAULT_VIEW, instrument))
            self._instrument_view_instrument_matches[instrument] = view_instrument_matches

            return view_instrument_matches

    def consume_measurement(self, measurement: Measurement, should_sample_exemplar: bool = True) -> None:
        """Hand one measurement to every stream of its instrument.

        A measurement from an instrument seen for the first time triggers the
        view matching, so the first recording on an instrument is the one that
        pays for it.

        Args:
            measurement: The measurement, which names the instrument it came
                from.
            should_sample_exemplar: Whether the aggregations may keep this
                measurement as an exemplar. Passed through unchanged.
        """
        for view_instrument_match in self._get_or_init_view_instrument_match(measurement.instrument):
            view_instrument_match.consume_measurement(measurement, should_sample_exemplar)

    def collect(self) -> MetricsData | None:
        """Gather every stream of every instrument into one batch.

        The shape of the data of a metric follows the class of the stream's
        aggregation: a sum becomes ``Sum``, marked monotonic when the
        instrument is a counter or an observable counter, a last value becomes
        ``Gauge``, and the two histogram aggregations become ``Histogram`` and
        ``ExponentialHistogram``. A stream aggregated with the drop
        aggregation contributes no metric at all.

        Metrics are grouped into one ``ScopeMetrics`` per instrumentation
        scope, so two instruments created by the same meter are reported
        together. The name and the description are the stream's, which a view
        may have overridden, while the unit is always the instrument's.

        One timestamp is taken before anything is collected and given to every
        aggregation, so the data points of a single batch share an end time.

        Returns:
            The batch, holding a single ``ResourceMetrics`` for the provider's
            resource, or ``None`` when no stream produced a data point.
        """
        # Use a list instead of yielding to prevent a slow reader from holding
        # SDK locks

        # While holding the lock, new _ViewInstrumentMatch can't be added from
        # another thread (so we are sure we collect all existing view).
        # However, instruments can still send measurements that will make it
        # into the individual aggregations; collection will acquire those locks
        # iteratively to keep locking as fine-grained as possible. One side
        # effect is that end times can be slightly skewed among the metric
        # streams produced by the SDK, but we still align the output timestamps
        # for a single instrument.

        collection_start_nanos = time_ns()

        with self._lock:
            instrumentation_scope_scope_metrics: dict[InstrumentationScope, ScopeMetrics] = {}

            instrument_matches_snapshot = list(self._instrument_view_instrument_matches.items())

            for (
                instrument,
                view_instrument_matches,
            ) in instrument_matches_snapshot:
                aggregation_temporality = self._instrument_class_temporality[instrument.__class__]

                metrics: list[Metric] = []

                for view_instrument_match in view_instrument_matches:
                    data_points = view_instrument_match.collect(aggregation_temporality, collection_start_nanos)

                    if data_points is None:
                        continue

                    if isinstance(
                        # pylint: disable=protected-access
                        view_instrument_match._aggregation,
                        _SumAggregation,
                    ):
                        data = Sum(
                            aggregation_temporality=aggregation_temporality,
                            data_points=data_points,
                            is_monotonic=isinstance(instrument, (Counter, ObservableCounter)),
                        )
                    elif isinstance(
                        # pylint: disable=protected-access
                        view_instrument_match._aggregation,
                        _LastValueAggregation,
                    ):
                        data = Gauge(data_points=data_points)
                    elif isinstance(
                        # pylint: disable=protected-access
                        view_instrument_match._aggregation,
                        _ExplicitBucketHistogramAggregation,
                    ):
                        data = Histogram(
                            data_points=data_points,
                            aggregation_temporality=aggregation_temporality,
                        )
                    elif isinstance(
                        # pylint: disable=protected-access
                        view_instrument_match._aggregation,
                        _DropAggregation,
                    ):
                        continue

                    elif isinstance(
                        # pylint: disable=protected-access
                        view_instrument_match._aggregation,
                        _ExponentialBucketHistogramAggregation,
                    ):
                        data = ExponentialHistogram(
                            data_points=data_points,
                            aggregation_temporality=aggregation_temporality,
                        )

                    metrics.append(
                        Metric(
                            # pylint: disable=protected-access
                            # pylint: disable=possibly-used-before-assignment
                            name=view_instrument_match._name,
                            description=view_instrument_match._description,
                            unit=view_instrument_match._instrument.unit,
                            data=data,
                        )
                    )

                if metrics:
                    if instrument.instrumentation_scope not in (instrumentation_scope_scope_metrics):
                        instrumentation_scope_scope_metrics[instrument.instrumentation_scope] = ScopeMetrics(
                            scope=instrument.instrumentation_scope,
                            metrics=metrics,
                            schema_url=instrument.instrumentation_scope.schema_url,
                        )
                    else:
                        instrumentation_scope_scope_metrics[instrument.instrumentation_scope].metrics.extend(metrics)

            if instrumentation_scope_scope_metrics:
                return MetricsData(
                    resource_metrics=[
                        ResourceMetrics(
                            resource=self._sdk_config.resource,
                            scope_metrics=list(instrumentation_scope_scope_metrics.values()),
                            schema_url=self._sdk_config.resource.schema_url,
                        )
                    ]
                )

            return None

    def _handle_view_instrument_match(
        self,
        instrument: _Instrument,
        view_instrument_matches: list["_ViewInstrumentMatch"],
    ) -> None:
        """Append one stream per view that selects the instrument.

        The views are walked in the order they were configured. A view that
        does not select the instrument is skipped silently, and one that
        selects it but cannot be applied to it is skipped with a warning
        logged by the compatibility check.

        Each new stream is compared against every stream already stored for an
        instrument matched earlier, and a warning naming both views is logged
        for each pair that would carry the same metric identity. The warning
        is all that happens: the stream is appended either way, and the
        exporter receives both. Streams built in this same call are not
        compared against each other, so two views that collide on the very
        same instrument go unreported.

        Args:
            instrument: The instrument being matched.
            view_instrument_matches: The list the new streams are appended to.
                The caller owns it and reads the result from it, since nothing
                is returned.
        """
        for view in self._sdk_config.views:
            # pylint: disable=protected-access
            if not view._match(instrument):
                continue

            if not self._check_view_instrument_compatibility(view, instrument):
                continue

            new_view_instrument_match = self._new_view_instrument_match(view, instrument)

            for existing_view_instrument_matches in self._instrument_view_instrument_matches.values():
                for existing_view_instrument_match in existing_view_instrument_matches:
                    if existing_view_instrument_match.conflicts(new_view_instrument_match):
                        _logger.warning(
                            "Views %s and %s will cause conflicting metrics identities",
                            existing_view_instrument_match._view,
                            new_view_instrument_match._view,
                        )

            view_instrument_matches.append(new_view_instrument_match)

    @staticmethod
    def _check_view_instrument_compatibility(view: View, instrument: _Instrument) -> bool:
        """
        Checks if a view and an instrument are compatible.

        Returns `true` if they are compatible and a `_ViewInstrumentMatch`
        object should be created, `false` otherwise.

        One pairing is rejected: an asynchronous instrument aggregated by
        either of the two histogram aggregations, which would bucket a running
        total instead of the individual values. Rejecting it logs a warning
        and leaves the instrument to the other views, or to the default view
        when no other view selects it.

        Args:
            view: The view that selected the instrument.
            instrument: The instrument the view selected.

        Returns:
            ``False`` for the rejected pairing described above, ``True`` for
            everything else, including a view whose aggregation makes no sense
            for the instrument in a way this check does not look for.
        """

        result = True

        # pylint: disable=protected-access
        if isinstance(instrument, Asynchronous) and isinstance(
            view._aggregation,
            (
                ExplicitBucketHistogramAggregation,
                ExponentialBucketHistogramAggregation,
            ),
        ):
            _logger.warning(
                "View %s and instrument %s will produce semantic errors when matched, the view has not been applied.",
                view,
                instrument,
            )
            result = False

        return result
