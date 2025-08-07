from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._sampler import ConsistentSampler
from ._util import MIN_THRESHOLD

_intent = SamplingIntent(threshold=MIN_THRESHOLD)


class ConsistentAlwaysOnSampler(ComposableSampler):
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
        return "ConsistentAlwaysOnSampler"


_always_on = ConsistentSampler(ConsistentAlwaysOnSampler())


def consistent_always_on() -> ConsistentSampler:
    """Returns a consistent sampler that samples all spans."""
    return _always_on
