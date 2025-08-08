from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState, get_current_span
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._sampler import ConsistentSampler
from ._trace_state import OtelTraceState
from ._util import (
    INVALID_THRESHOLD,
    MIN_THRESHOLD,
    is_valid_threshold,
)


class ConsistentParentBasedSampler(ComposableSampler):
    def __init__(self, root_sampler: ComposableSampler):
        self._root_sampler = root_sampler
        self._description = f"ConsistentParentBasedSampler{{root_sampler={root_sampler.get_description()}}}"

    def sampling_intent(
        self,
        parent_ctx: Optional[Context],
        name: str,
        span_kind: Optional[SpanKind],
        attributes: Attributes,
        links: Optional[Sequence[Link]],
        trace_state: Optional[TraceState] = None,
    ) -> SamplingIntent:
        parent_span = get_current_span(parent_ctx)
        parent_span_ctx = parent_span.get_span_context()
        is_root = not parent_span_ctx.is_valid
        if is_root:
            return self._root_sampler.sampling_intent(
                parent_ctx, name, span_kind, attributes, links, trace_state
            )

        ot_trace_state = OtelTraceState.parse(trace_state)

        if is_valid_threshold(ot_trace_state.threshold):
            return SamplingIntent(
                threshold=ot_trace_state.threshold,
                adjusted_count_reliable=True,
            )

        threshold = (
            MIN_THRESHOLD
            if parent_span_ctx.trace_flags.sampled
            else INVALID_THRESHOLD
        )
        return SamplingIntent(
            threshold=threshold, adjusted_count_reliable=False
        )

    def get_description(self) -> str:
        return self._description


def consistent_parent_based(
    root_sampler: ComposableSampler,
) -> ConsistentSampler:
    """Returns a consistent sampler that respects the sampling decision of
    the parent span or falls-back to the given sampler if it is a root span."""
    return ConsistentSampler(ConsistentParentBasedSampler(root_sampler))
