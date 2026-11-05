# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The bridge from a composable sampler to the SDK ``Sampler`` interface.

A composable sampler produces a threshold. This module turns that threshold
into a decision by comparing it against a 56-bit randomness value, and then
writes the result back into the ``ot`` trace state entry so that children of
the span inherit it.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._trace_state import OTEL_TRACE_STATE_KEY, OtelTraceState
from ._util import INVALID_THRESHOLD, is_valid_random_value, is_valid_threshold


class _CompositeSampler(Sampler):
    """A ``Sampler`` that takes its threshold from a composable sampler.

    The instance holds no per-span state, so one is enough for a whole tracer
    provider.

    Args:
        delegate: The composable sampler asked for a threshold on every span.
            Its description is also reported as this sampler's description.
    """

    def __init__(self, delegate: ComposableSampler):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._delegate = delegate

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Decide whether a span about to be created is sampled.

        The threshold comes from the delegate. The randomness it is compared
        against is the ``rv`` field of the incoming ``ot`` trace state entry
        when that field is valid, and otherwise the low 56 bits of
        ``trace_id``. The trace flags are not consulted, so the low bits of
        the trace id are used whether or not the parent advertised the trace
        id as random. The span is sampled when the threshold is less than or
        equal to the randomness, which is why a lower threshold samples more.

        An invalid threshold short circuits the comparison and drops the span.

        The outgoing ``ot`` entry repeats the threshold only when the span was
        sampled and the delegate marked the threshold reliable. Otherwise
        ``th`` is left out of the entry the composite sampler writes. That
        entry is written only when it serializes to a non-empty string, so a
        parent ``ot`` entry that held nothing but ``th`` is passed on to the
        child unchanged and the child does inherit that threshold.

        Args:
            parent_context: Context holding the parent span, or ``None`` to
                mean the current context. Passed to the delegate unchanged.
            trace_id: The trace id of the span being created. Only its low 56
                bits are read, and only when the ``ot`` entry carries no
                usable ``rv``.
            name: The name the span will be created with.
            kind: The kind the span will be created with, or ``None``.
            attributes: The attributes known at creation time, or ``None``.
                The result carries the delegate's attributes, not these.
            links: The links the span will be created with, or ``None``.
            trace_state: The trace state inherited from the parent, or
                ``None``.

        Returns:
            A result whose decision is ``Decision.RECORD_AND_SAMPLE`` or
            ``Decision.DROP``, whose attributes are the ones the delegate
            asked for, and whose trace state carries the updated ``ot`` entry.
            The trace state is ``None`` when there was none to start with and
            nothing needed writing.
        """
        ot_trace_state = OtelTraceState.parse(trace_state)

        intent = self._delegate.sampling_intent(parent_context, name, kind, attributes, links, trace_state)
        threshold = intent.threshold

        if is_valid_threshold(threshold):
            adjusted_count_correct = intent.threshold_reliable
            if is_valid_random_value(ot_trace_state.random_value):
                randomness = ot_trace_state.random_value
            else:
                # Use last 56 bits of trace_id as randomness
                randomness = trace_id & 0x00FFFFFFFFFFFFFF
            sampled = threshold <= randomness
        else:
            sampled = False
            adjusted_count_correct = False

        decision = Decision.RECORD_AND_SAMPLE if sampled else Decision.DROP
        if sampled and adjusted_count_correct:
            ot_trace_state.threshold = threshold
        else:
            ot_trace_state.threshold = INVALID_THRESHOLD

        return SamplingResult(
            decision,
            intent.attributes,
            _update_trace_state(trace_state, ot_trace_state, intent),
        )

    def get_description(self) -> str:
        """Describe the sampler.

        Returns:
            The delegate's own description, unwrapped. Nothing identifies the
            composite sampler itself, so two tracer providers wrapping the
            same composable sampler report the same string.
        """
        return self._delegate.get_description()


def _update_trace_state(
    trace_state: TraceState | None,
    ot_trace_state: OtelTraceState,
    intent: SamplingIntent,
) -> TraceState | None:
    """Build the trace state the new span will carry.

    The ``ot`` entry is written last, so it overrides any ``ot`` the intent's
    own update produced. The intent's update is skipped entirely when there is
    no incoming trace state.

    Args:
        trace_state: The trace state inherited from the parent, or ``None``.
        ot_trace_state: The parsed ``ot`` entry, already carrying the
            threshold the decision was made with.
        intent: The intent returned by the composable sampler, consulted only
            for its ``update_trace_state`` callable.

    Returns:
        A new trace state, or ``None`` when there was no incoming trace state
        and the ``ot`` entry serialized to the empty string.
    """
    otts = ot_trace_state.serialize()
    if not trace_state:
        if otts:
            return TraceState(((OTEL_TRACE_STATE_KEY, otts),))
        return None
    new_trace_state = intent.update_trace_state(trace_state)
    if otts:
        return new_trace_state.update(OTEL_TRACE_STATE_KEY, otts)
    return new_trace_state


def composite_sampler(delegate: ComposableSampler) -> Sampler:
    """A sampler that uses a a composable sampler to make its decision while
    handling tracestate.

    Args:
        delegate: The composable sampler to use for making sampling decisions.

    Returns:
        A ``Sampler`` a tracer provider accepts. It holds no state of its own,
        so one instance serves every span.
    """
    return _CompositeSampler(delegate)
