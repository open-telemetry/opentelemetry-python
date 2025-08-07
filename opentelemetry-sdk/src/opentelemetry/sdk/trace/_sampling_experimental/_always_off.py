from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._sampler import ConsistentSampler
from ._util import INVALID_THRESHOLD

_intent = SamplingIntent(
    threshold=INVALID_THRESHOLD, adjusted_count_reliable=False
)


class ConsistentAlwaysOffSampler(ComposableSampler):
    def sampling_intent(
        self,
        parent_ctx: Optional[Context],
        name: str,
        span_kind: Optional[SpanKind],
        attributes: Attributes,
        links: Optional[Sequence[Link]],
        trace_state: Optional[TraceState] = None,
    ) -> SamplingIntent:
        return _intent

    def get_description(self) -> str:
        return "ConsistentAlwaysOffSampler"


_always_off = ConsistentSampler(ConsistentAlwaysOffSampler())


def consistent_always_off() -> ConsistentSampler:
    """Returns a consistent sampler that does not sample any span."""
    return _always_off
