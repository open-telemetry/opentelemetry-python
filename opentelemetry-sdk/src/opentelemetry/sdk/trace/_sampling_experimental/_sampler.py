from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._trace_state import OTEL_TRACE_STATE_KEY, OtelTraceState
from ._util import INVALID_THRESHOLD, is_valid_random_value, is_valid_threshold


class ConsistentSampler(Sampler, ComposableSampler):
    """A sampler that uses a consistent sampling strategy based on a delegate sampler."""

    def __init__(self, delegate: ComposableSampler):
        self._delegate = delegate

    def should_sample(
        self,
        parent_context: Optional[Context],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence[Link]] = None,
        trace_state: Optional[TraceState] = None,
    ) -> SamplingResult:
        ot_trace_state = OtelTraceState.parse(trace_state)

        intent = self._delegate.sampling_intent(
            parent_context, name, kind, attributes, links, trace_state
        )
        threshold = intent.threshold

        if is_valid_threshold(threshold):
            adjusted_count_correct = intent.adjusted_count_reliable
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

        otts = ot_trace_state.serialize()
        if not trace_state:
            if otts:
                new_trace_state = TraceState(((OTEL_TRACE_STATE_KEY, otts),))
            else:
                new_trace_state = None
        else:
            new_trace_state = intent.update_trace_state(trace_state)
            if otts:
                new_trace_state = new_trace_state.update(
                    OTEL_TRACE_STATE_KEY, otts
                )

        return SamplingResult(decision, intent.attributes, new_trace_state)

    def sampling_intent(
        self,
        parent_ctx: Optional[Context],
        name: str,
        span_kind: Optional[SpanKind],
        attributes: Attributes,
        links: Optional[Sequence[Link]],
        trace_state: Optional[TraceState],
    ) -> SamplingIntent:
        return self._delegate.sampling_intent(
            parent_ctx, name, span_kind, attributes, links, trace_state
        )

    def get_description(self) -> str:
        return self._delegate.get_description()
