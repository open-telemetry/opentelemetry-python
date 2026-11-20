# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A ``unittest`` base class that captures spans and metrics in memory.

:class:`TestBase` wires a tracer provider and a meter provider that keep
everything they are given in process, installs them as the API globals, and
exposes the captured telemetry to assertions. No exporter reaches the network,
so a test that uses it needs no collector and no port.

The module also provides :class:`FinishedTestSpans`, the list subclass that
:meth:`TestBase.get_finished_spans` returns, which can look a span up by name or
by attribute and fails the test instead of returning ``None`` when nothing
matches.
"""

import logging
import unittest
from collections.abc import Sequence
from contextlib import contextmanager

from opentelemetry import metrics as metrics_api
from opentelemetry import trace as trace_api
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES,
)
from opentelemetry.sdk.metrics._internal.point import Metric
from opentelemetry.sdk.metrics.export import (
    DataPointT,
    HistogramDataPoint,
    InMemoryMetricReader,
    MetricReader,
    NumberDataPoint,
)
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.test.globals_test import (
    reset_metrics_globals,
    reset_trace_globals,
)


class TestBase(unittest.TestCase):
    """Base class for a test that needs to assert on emitted telemetry.

    ``setUp`` installs a fresh tracer provider and meter provider as the API
    globals, each feeding an in-memory sink, and ``tearDown`` removes them
    again, so instrumentation under test reaches this class through the ordinary
    ``opentelemetry.trace.get_tracer`` and ``opentelemetry.metrics.get_meter``
    calls and needs no test-specific wiring of its own.

    The captured telemetry is reachable in three ways. ``self.memory_exporter``
    is the span exporter, ``self.memory_metrics_reader`` is the metric reader,
    and the ``get_finished_spans`` and ``get_sorted_metrics`` methods read from
    them. Every test method gets its own providers, so nothing recorded by one
    test is visible to another.

    Override the ``create_tracer_provider`` or ``create_meter_provider``
    staticmethod to pass arguments to a provider, forwarding ``**kwargs`` to
    the ``TestBase`` implementation. ``setUp`` calls the override and installs
    what it returns as the API global. Reassigning ``self.tracer_provider``
    after ``super().setUp()`` does not work: the provider built by ``setUp`` is
    already the installed global, and ``set_tracer_provider`` will not replace
    it, so instrumentation keeps reporting to it while the reassigned exporter
    stays empty.
    """

    # pylint: disable=C0103

    def setUp(self):
        """Install in-memory trace and metrics pipelines as the API globals.

        Resets the trace and metrics globals first, because
        ``set_tracer_provider`` and ``set_meter_provider`` ignore the call when
        a provider is already configured, which would otherwise leave this test
        reading the telemetry of whichever test ran first.
        """
        super().setUp()
        result = self.create_tracer_provider()
        self.tracer_provider, self.memory_exporter = result
        # This is done because set_tracer_provider cannot override the
        # current tracer provider.
        reset_trace_globals()
        trace_api.set_tracer_provider(self.tracer_provider)

        self.memory_exporter.clear()
        # This is done because set_meter_provider cannot override the
        # current meter provider.
        reset_metrics_globals()
        (
            self.meter_provider,
            self.memory_metrics_reader,
        ) = self.create_meter_provider()
        metrics_api.set_meter_provider(self.meter_provider)

    def tearDown(self):
        """Unset the trace and metrics globals installed by ``setUp``.

        The providers and their in-memory sinks are not shut down, so a span or
        a metric reached for after the test method has returned is still
        readable through the attributes ``setUp`` assigned.
        """
        super().tearDown()
        reset_trace_globals()
        reset_metrics_globals()

    def get_finished_spans(self):
        """Return the spans ended so far, in the order they were exported.

        Returns:
            A :class:`FinishedTestSpans` over the spans the in-memory exporter
            holds, which supports ``by_name`` and ``by_attr`` lookups on top of
            the usual list operations. The list is a snapshot: a span ended
            after this call does not appear in it.
        """
        return FinishedTestSpans(self, self.memory_exporter.get_finished_spans())

    def assertEqualSpanInstrumentationScope(self, span, module):
        """Assert that a span was produced by the tracer of a given module.

        Instrumentation is expected to name its tracer after its own module and
        version, so this checks both at once rather than leaving a test to spell
        out two ``assertEqual`` calls.

        Args:
            span: The span to inspect. Its ``instrumentation_scope`` is read, so
                it has to be an SDK span and not a non-recording one.
            module: The module object the span is expected to come from. Its
                ``__name__`` is compared against the scope name first, and its
                ``__version__`` against the scope version only once that
                comparison has passed. A module without ``__version__``
                therefore raises ``AttributeError`` rather than failing the
                assertion, but only when its ``__name__`` already matches; a
                name mismatch fails the first assertion and never reads
                ``__version__``.
        """
        self.assertEqual(span.instrumentation_scope.name, module.__name__)
        self.assertEqual(span.instrumentation_scope.version, module.__version__)

    def assertSpanHasAttributes(self, span, attributes):
        """Assert that a span carries at least the given attributes.

        Each key has to be present and to compare equal. Attributes the span
        carries beyond the given ones are ignored, so this does not detect an
        attribute that should have been dropped.

        Args:
            span: The span whose ``attributes`` mapping is checked.
            attributes: Mapping of attribute key to expected value.
        """
        for key, val in attributes.items():
            self.assertIn(key, span.attributes)
            self.assertEqual(val, span.attributes[key])

    def sorted_spans(self, spans):  # pylint: disable=R0201
        """
        Sorts spans by span creation time.

        Note: This method should not be used to sort spans in a deterministic way as the
        order depends on timing precision provided by the platform.

        Args:
            spans: The spans to sort. Their private ``_start_time`` is read, so
                they have to be SDK spans.

        Returns:
            A new list holding the same spans, newest first. The argument is not
            modified.
        """
        return sorted(
            spans,
            key=lambda s: s._start_time,  # pylint: disable=W0212
            reverse=True,
        )

    @staticmethod
    def create_tracer_provider(**kwargs):
        """Helper to create a configured tracer provider.

        Creates and configures a `TracerProvider` with a
        `SimpleSpanProcessor` and a `InMemorySpanExporter`.
        All the parameters passed are forwarded to the TracerProvider
        constructor.

        Args:
            **kwargs: Forwarded unchanged to the ``TracerProvider``
                constructor, for example ``resource`` or ``sampler``.

        Returns:
            A tuple with the tracer provider in the first element and the
            in-memory span exporter in the second.
        """
        tracer_provider = TracerProvider(**kwargs)
        memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)

        return tracer_provider, memory_exporter

    @staticmethod
    def create_meter_provider(**kwargs) -> tuple[MeterProvider, MetricReader]:
        """Helper to create a configured meter provider.

        Creates a `MeterProvider` and an `InMemoryMetricReader`.

        Args:
            **kwargs: Forwarded unchanged to the ``MeterProvider``
                constructor. A ``metric_readers`` list given here is appended
                to rather than replaced, and the list object passed in is
                mutated, so the in-memory reader is added alongside any reader
                the caller supplies.

        Returns:
            A tuple with the meter provider in the first element and the
            in-memory metric reader in the second.
        """
        memory_reader = InMemoryMetricReader()
        metric_readers = kwargs.get("metric_readers", [])
        metric_readers.append(memory_reader)
        kwargs["metric_readers"] = metric_readers
        meter_provider = MeterProvider(**kwargs)
        return meter_provider, memory_reader

    @staticmethod
    @contextmanager
    def disable_logging(highest_level=logging.CRITICAL):
        """Silence the ``logging`` module for the duration of the block.

        Use it around code that is expected to log an error, so the failure
        under test does not fill the output of a passing run.

        Args:
            highest_level: The highest level to suppress. Everything at this
                level and below is dropped, so the default of
                ``logging.CRITICAL`` suppresses every record.

        Yields:
            ``None``. The block runs with logging suppressed, and suppression is
            lifted on exit whether the block completed or raised. Suppression is
            process-wide, so a thread logging concurrently is silenced too.
        """
        logging.disable(highest_level)

        try:
            yield
        finally:
            logging.disable(logging.NOTSET)

    def get_sorted_metrics(self, scope: str | None = None):
        """Returns recorded metrics sorted by name.

        Args:
            scope: Optional scope name to filter metrics by. If unset,
                   all metrics are returned. A name that matches no scope
                   yields an empty list rather than an error.

        Returns:
            The metrics the reader holds after a fresh collection, sorted by
            name. Reading them performs that collection. ``create_meter_provider``
            builds the reader with the default cumulative temporality, so a
            measurement already reported is reported again on every later call
            and the values accumulate rather than reset. Calling this twice with
            nothing recorded in between returns the same values twice.
        """
        metrics_data = self.memory_metrics_reader.get_metrics_data()
        resource_metrics = metrics_data.resource_metrics if metrics_data else []

        all_metrics = []
        for metrics in resource_metrics:
            for scope_metrics in metrics.scope_metrics:
                if scope is not None and scope_metrics.scope.name != scope:
                    continue
                all_metrics.extend(scope_metrics.metrics)

        return self.sorted_metrics(all_metrics)

    @staticmethod
    def sorted_metrics(metrics):
        """
        Sorts metrics by metric name.

        Args:
            metrics: The metrics to sort.

        Returns:
            A new list holding the same metrics in ascending name order. The
            argument is not modified.
        """
        return sorted(
            metrics,
            key=lambda m: m.name,
        )

    def assert_metric_expected(
        self,
        metric: Metric,
        expected_data_points: Sequence[DataPointT],
        est_value_delta: float | None = 0,
    ):
        """Assert that a metric carries exactly the expected data points.

        The counts have to match, and every expected data point has to have a
        match somewhere in the metric. Order is not compared, so a data point
        may appear anywhere in the metric.

        Args:
            metric: The metric to check.
            expected_data_points: The data points the metric is expected to
                carry.
            est_value_delta: Tolerance on the numeric value, for a measurement
                that cannot be predicted exactly, such as a duration. Passing
                ``0`` demands equality and additionally demands that the
                ``min`` and ``max`` of a histogram data point match.
        """
        self.assertEqual(len(expected_data_points), len(metric.data.data_points))
        for expected_data_point in expected_data_points:
            self.assert_data_point_expected(expected_data_point, metric.data.data_points, est_value_delta)

    # pylint: disable=unidiomatic-typecheck
    @staticmethod
    def is_data_points_equal(
        expected_data_point: DataPointT,
        data_point: DataPointT,
        est_value_delta: float | None = 0,
    ):
        """Report whether two data points describe the same measurement.

        Args:
            expected_data_point: The data point a test is looking for.
            data_point: The data point that was recorded.
            est_value_delta: Largest difference in value that still counts as
                equal. When it is ``0``, the ``min`` and ``max`` of a histogram
                data point also have to match exactly.

        Returns:
            ``True`` when the two are of the same concrete type, that type is
            ``NumberDataPoint`` or ``HistogramDataPoint``, their values agree
            within ``est_value_delta``, and their attributes are equal. Two
            ``HistogramDataPoint`` objects additionally have to carry the same
            ``count`` and the same ``explicit_bounds``, and the same ``min`` and
            ``max`` when ``est_value_delta`` is ``0``. A data point of any other
            type returns ``False`` rather than raising, so an unsupported type
            is reported as a mismatch.
        """
        if type(expected_data_point) != type(data_point) or not isinstance(  # noqa: E721
            expected_data_point, (HistogramDataPoint, NumberDataPoint)
        ):
            return False

        values_diff = None
        if isinstance(data_point, NumberDataPoint):
            values_diff = abs(expected_data_point.value - data_point.value)
        elif isinstance(data_point, HistogramDataPoint):
            values_diff = abs(expected_data_point.sum - data_point.sum)
            if expected_data_point.count != data_point.count or (
                est_value_delta == 0
                and (expected_data_point.min != data_point.min or expected_data_point.max != data_point.max)
            ):
                return False

            if expected_data_point.explicit_bounds != data_point.explicit_bounds:
                return False

        return values_diff <= est_value_delta and expected_data_point.attributes == dict(data_point.attributes)

    def assert_data_point_expected(
        self,
        expected_data_point: DataPointT,
        data_points: Sequence[DataPointT],
        est_value_delta: float | None = 0,
    ):
        """Assert that one of the recorded data points matches the expected one.

        Fails the test naming the expected data point when none of them does.

        Args:
            expected_data_point: The data point a test is looking for.
            data_points: The recorded data points to search, in any order.
            est_value_delta: Tolerance passed on to ``is_data_points_equal``.
        """
        is_data_point_exist = False
        for data_point in data_points:
            if self.is_data_points_equal(expected_data_point, data_point, est_value_delta):
                is_data_point_exist = True
                break

        self.assertTrue(
            is_data_point_exist,
            msg=f"Data point {expected_data_point} does not exist",
        )

    @staticmethod
    def create_number_data_point(value, attributes):
        """Build a ``NumberDataPoint`` to compare a recorded one against.

        Both timestamps are set to ``0``, because ``is_data_points_equal``
        ignores them and a test cannot predict the real ones.

        Args:
            value: The expected value of the counter or gauge.
            attributes: The expected attributes of the data point.

        Returns:
            A ``NumberDataPoint`` carrying the given value and attributes.
        """
        return NumberDataPoint(
            value=value,
            attributes=attributes,
            start_time_unix_nano=0,
            time_unix_nano=0,
        )

    @staticmethod
    def create_histogram_data_point(
        sum_data_point,
        count,
        max_data_point,
        min_data_point,
        attributes,
        explicit_bounds=None,
    ):
        """Build a ``HistogramDataPoint`` to compare a recorded one against.

        Both timestamps are set to ``0`` and ``bucket_counts`` to an empty list,
        because ``is_data_points_equal`` compares neither.

        Args:
            sum_data_point: The expected sum of the recorded measurements.
            count: The expected number of recorded measurements.
            max_data_point: The expected largest recorded measurement. It is
                compared only when ``est_value_delta`` is ``0``.
            min_data_point: The expected smallest recorded measurement, compared
                under the same condition.
            attributes: The expected attributes of the data point.
            explicit_bounds: The expected bucket boundaries. When ``None``, the
                SDK default boundaries are used, which is what an instrument
                configured with no explicit view reports.

        Returns:
            A ``HistogramDataPoint`` carrying the given values.
        """
        return HistogramDataPoint(
            count=count,
            sum=sum_data_point,
            min=min_data_point,
            max=max_data_point,
            attributes=attributes,
            start_time_unix_nano=0,
            time_unix_nano=0,
            bucket_counts=[],
            explicit_bounds=explicit_bounds
            if explicit_bounds is not None
            else _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES,
        )


class FinishedTestSpans(list):
    """A list of ended spans that can look one up and fail the test if absent.

    Returned by :meth:`TestBase.get_finished_spans`. Every ``list`` operation
    works on it. The ``by_name`` and ``by_attr`` lookups exist so that a missing
    span is reported as a named test failure rather than as an
    ``AttributeError`` on ``None`` several lines later.

    Args:
        test: The test case to call ``fail`` on when a lookup finds nothing.
        spans: The ended spans, copied into this list in the order given.
    """

    def __init__(self, test, spans):
        """Parameters are documented on the class docstring."""
        super().__init__(spans)
        self.test = test

    def by_name(self, name):
        """Return the first span with a given name, failing the test if absent.

        Args:
            name: The exact span name to look for. Matching is by equality, not
                by substring or pattern.

        Returns:
            The first span in this list whose name matches. When no span
            matches, the test case is failed, so the ``None`` in the return
            statement is never the value a caller sees under the default
            ``unittest`` runner.
        """
        for span in self:
            if span.name == name:
                return span
        self.test.fail(f"Did not find span with name {name}")
        return None

    def by_attr(self, key, value):
        """Return the first span carrying a given attribute value.

        Args:
            key: The attribute key to read.
            value: The value that key is expected to have. A span that does not
                carry the key at all is treated as a span whose value is
                ``None``, so passing ``None`` here matches such a span.

        Returns:
            The first span in this list whose attribute matches. When no span
            matches, the test case is failed, so the ``None`` in the return
            statement is never the value a caller sees under the default
            ``unittest`` runner.
        """
        for span in self:
            if span.attributes.get(key) == value:
                return span
        self.test.fail(f"Did not find span with attrs {key}={value}")
        return None
