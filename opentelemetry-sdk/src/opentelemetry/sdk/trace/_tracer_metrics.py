# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Self-observability metrics the SDK records about its own span creation.

Two instruments are recorded here, both created from the semantic conventions
and both reported by a meter named ``opentelemetry-sdk``. ``otel.sdk.span.started``
counts every span the SDK creates. ``otel.sdk.span.live`` tracks how many
recording spans have been created and not yet ended.

``Tracer`` builds one of these objects through ``create_tracer_metrics`` and
calls ``start_span`` on it for each span. Whether real instruments or no-op
ones are used is decided by the ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``
environment variable, which the caller parses and passes in as ``enabled``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_SPAN_PARENT_ORIGIN,
    OTEL_SPAN_SAMPLING_RESULT,
    OtelSpanSamplingResultValues,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_span_live,
    create_otel_sdk_span_started,
)
from opentelemetry.trace.span import SpanContext


class TracerMetricsT(Protocol):
    """Interface ``Tracer`` uses to report span creation to itself.

    Both ``TracerMetrics`` and ``NoOpTracerMetrics`` satisfy this protocol, so
    the caller treats an enabled and a disabled build the same way.
    """

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        """Record that a span has been created.

        Args:
            parent_span_context: Span context of the parent, or ``None`` for a
                root span.
            sampling_decision: Decision the sampler returned for this span.

        Returns:
            A callable the caller must invoke when the span ends.
        """
        ...  # pylint: disable=unnecessary-ellipsis


# pylint: disable=no-self-use
class NoOpTracerMetrics:
    """Implementation that records nothing.

    Used when self-observability metrics are turned off, so that ``Tracer``
    pays only an attribute lookup and a call per span.
    """

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        """Ignore the span.

        Args:
            parent_span_context: Ignored.
            sampling_decision: Ignored.

        Returns:
            ``noop``, which does nothing when the span ends.
        """
        return noop


class TracerMetrics:
    """Implementation that records ``otel.sdk.span.started`` and ``otel.sdk.span.live``.

    One instance is built per ``Tracer``, and each one asks a meter named
    ``opentelemetry-sdk`` for the two instruments. The meter creates them on
    the first request and returns the same pair to every later one, so all
    the tracers reaching one meter provider record into a single pair of
    instruments.

    Args:
        meter_provider: Provider the two instruments are created from.
    """

    def __init__(self, meter_provider: metrics_api.MeterProvider) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        meter = meter_provider.get_meter("opentelemetry-sdk")

        self._started_spans = create_otel_sdk_span_started(meter)
        self._live_spans = create_otel_sdk_span_live(meter)

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        """Add one to ``otel.sdk.span.started`` and, when recording, to ``otel.sdk.span.live``.

        ``otel.sdk.span.started`` is incremented for every span, including
        dropped ones, and carries ``otel.span.parent.origin`` and
        ``otel.span.sampling_result``. ``otel.sdk.span.live`` is only touched
        when the decision is recording, and carries
        ``otel.span.sampling_result`` alone.

        Args:
            parent_span_context: Span context of the parent, or ``None``.
                It decides the value of ``otel.span.parent.origin``.
            sampling_decision: Decision the sampler returned. It decides the
                value of ``otel.span.sampling_result`` and whether the live
                count is touched at all.

        Returns:
            A callable that subtracts one from ``otel.sdk.span.live`` when the
            span ends, or ``noop`` when the decision is not recording and
            nothing was added to that instrument.
        """
        sampling_result_value = sampling_result(sampling_decision)
        self._started_spans.add(
            1,
            {
                OTEL_SPAN_PARENT_ORIGIN: parent_origin(parent_span_context),
                OTEL_SPAN_SAMPLING_RESULT: sampling_result_value,
            },
        )

        if not sampling_decision.is_recording():
            return noop

        live_span_attrs = {
            OTEL_SPAN_SAMPLING_RESULT: sampling_result_value,
        }
        self._live_spans.add(1, live_span_attrs)

        def end_span() -> None:
            """Subtract one from ``otel.sdk.span.live``.

            The same attributes used when the span was counted as live are
            reused, so the addition and the subtraction land on one time
            series.
            """
            self._live_spans.add(-1, live_span_attrs)

        return end_span


def create_tracer_metrics(
    meter_provider: metrics_api.MeterProvider,
    enabled: bool,
) -> TracerMetricsT:
    """Build the metrics recorder a ``Tracer`` should use.

    Args:
        meter_provider: Provider the instruments are created from. Only read
            when ``enabled`` is ``True``.
        enabled: Whether self-observability metrics are turned on, as parsed
            from ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.

    Returns:
        A ``TracerMetrics`` when ``enabled`` is ``True``, otherwise a
        ``NoOpTracerMetrics`` that creates no instruments.
    """
    if not enabled:
        return NoOpTracerMetrics()

    return TracerMetrics(meter_provider)


def noop() -> None:
    """Do nothing.

    Handed out by ``NoOpTracerMetrics.start_span``, and by
    ``TracerMetrics.start_span`` for a span that is not recording, so that the
    caller always has a callable to invoke when the span ends.
    """


def parent_origin(span_ctx: SpanContext | None) -> str:
    """Classify the parent of a span for the ``otel.span.parent.origin`` attribute.

    Args:
        span_ctx: Span context of the parent, or ``None`` for a root span.

    Returns:
        ``"none"`` when ``span_ctx`` is ``None``, ``"remote"`` when the parent
        was extracted from an incoming request, and ``"local"`` when the
        parent was created in this process.
    """
    if span_ctx is None:
        return "none"
    if span_ctx.is_remote:
        return "remote"
    return "local"


def sampling_result(decision: Decision) -> str:
    """Map a sampling decision to the ``otel.span.sampling_result`` attribute value.

    Args:
        decision: Decision the sampler returned for the span.

    Returns:
        The semantic convention string for the decision. Anything other than
        ``Decision.RECORD_AND_SAMPLE`` and ``Decision.RECORD_ONLY`` maps to
        the value for a dropped span.
    """
    if decision == Decision.RECORD_AND_SAMPLE:
        return OtelSpanSamplingResultValues.RECORD_AND_SAMPLE.value
    if decision == Decision.RECORD_ONLY:
        return OtelSpanSamplingResultValues.RECORD_ONLY.value
    return OtelSpanSamplingResultValues.DROP.value
