# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult, _get_parent_trace_state
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._trace_state import OTEL_TRACE_STATE_KEY, OtelTraceState
from ._util import INVALID_THRESHOLD, is_valid_random_value, is_valid_threshold


class _CompositeSampler(Sampler):
    def __init__(self, delegate: ComposableSampler):
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
        if trace_state is None:
            trace_state = _get_parent_trace_state(parent_context)
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
        return self._delegate.get_description()


def _update_trace_state(
    trace_state: TraceState | None,
    ot_trace_state: OtelTraceState,
    intent: SamplingIntent,
) -> TraceState | None:
    # The composite sampler owns `ot`; callbacks may update other tracestate keys.
    otts = ot_trace_state.serialize()
    # Apply the sampler's own update even when there is no incoming tracestate,
    # otherwise a composable sampler that stamps tracestate is silently skipped
    # for every root span.
    new_trace_state = intent.update_trace_state(trace_state or TraceState())
    if not new_trace_state:
        if otts:
            return TraceState(((OTEL_TRACE_STATE_KEY, otts),))
        return None
    if otts:
        return new_trace_state.update(OTEL_TRACE_STATE_KEY, otts)
    # CompositeSampler removes `th` for dropped spans or unreliable thresholds.
    # If nothing remains in `ot`, delete the incoming entry to avoid retaining a stale threshold.
    # https://opentelemetry.io/docs/specs/otel/trace/sdk/#compositesampler
    if OTEL_TRACE_STATE_KEY in new_trace_state:
        return new_trace_state.delete(OTEL_TRACE_STATE_KEY)
    return new_trace_state


def composite_sampler(delegate: ComposableSampler) -> Sampler:
    """A sampler that uses a a composable sampler to make its decision while
    handling tracestate.

    Args:
        delegate: The composable sampler to use for making sampling decisions.
    """
    return _CompositeSampler(delegate)
