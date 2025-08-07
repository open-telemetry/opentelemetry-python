from typing import Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._sampler import ConsistentSampler
from ._trace_state import serialize_th
from ._util import INVALID_THRESHOLD, MAX_THRESHOLD, calculate_threshold


class ConsistentFixedThresholdSampler(ComposableSampler):
    _threshold: int
    _description: str

    def __init__(self, sampling_probability: float):
        threshold = calculate_threshold(sampling_probability)
        if threshold == MAX_THRESHOLD:
            threshold_str = "max"
        else:
            threshold_str = serialize_th(threshold)
        threshold = (
            INVALID_THRESHOLD if threshold == MAX_THRESHOLD else threshold
        )
        self._intent = SamplingIntent(threshold=threshold)
        self._description = f"ConsistentFixedThresholdSampler{{threshold={threshold_str}, sampling probability={sampling_probability}}}"

    def sampling_intent(
        self,
        parent_ctx: Optional[Context],
        name: str,
        span_kind: Optional[SpanKind],
        attributes: Attributes,
        links: Optional[Sequence[Link]],
        trace_state: Optional[TraceState] = None,
    ) -> SamplingIntent:
        return self._intent

    def get_description(self) -> str:
        return self._description


def consistent_probability_based(
    sampling_probability: float,
) -> ConsistentSampler:
    """Returns a consistent sampler that samples each span with a fixed probability."""
    if not (0.0 <= sampling_probability <= 1.0):
        raise ValueError("Sampling probability must be between 0.0 and 1.0")

    return ConsistentSampler(
        ConsistentFixedThresholdSampler(sampling_probability)
    )
