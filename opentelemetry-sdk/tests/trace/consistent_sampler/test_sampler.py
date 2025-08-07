from typing import Optional

import pytest
from pytest import param as p

from opentelemetry.sdk.trace._sampling_experimental import (
    consistent_always_off,
    consistent_always_on,
    consistent_parent_based,
    consistent_probability_based,
)
from opentelemetry.sdk.trace._sampling_experimental._trace_state import (
    OtelTraceState,
)
from opentelemetry.sdk.trace._sampling_experimental._util import (
    INVALID_RANDOM_VALUE,
    INVALID_THRESHOLD,
)
from opentelemetry.sdk.trace.sampling import Decision, Sampler
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    TraceState,
    set_span_in_context,
)

TRACE_ID = int("00112233445566778800000000000000", 16)
SPAN_ID = int("0123456789abcdef", 16)


@pytest.mark.parametrize(
    "sampler,parent_sampled,parent_threshold,parent_random_value,sampled,threshold,random_value",
    (
        p(
            consistent_always_on(),
            True,
            None,
            None,
            True,
            0,
            INVALID_RANDOM_VALUE,
            id="min threshold no parent random value",
        ),
        p(
            consistent_always_on(),
            True,
            None,
            0x7F99AA40C02744,
            True,
            0,
            0x7F99AA40C02744,
            id="min threshold with parent random value",
        ),
        p(
            consistent_always_off(),
            True,
            None,
            None,
            False,
            INVALID_THRESHOLD,
            INVALID_RANDOM_VALUE,
            id="max threshold",
        ),
        p(
            consistent_parent_based(consistent_always_on()),
            False,  # should be ignored
            0x7F99AA40C02744,
            0x7F99AA40C02744,
            True,
            0x7F99AA40C02744,
            0x7F99AA40C02744,
            id="parent based in consistent mode",
        ),
        p(
            consistent_parent_based(consistent_always_on()),
            True,
            None,
            None,
            True,
            INVALID_THRESHOLD,
            INVALID_RANDOM_VALUE,
            id="parent based in legacy mode",
        ),
        p(
            consistent_probability_based(0.5),
            True,
            None,
            0x7FFFFFFFFFFFFF,
            False,
            INVALID_THRESHOLD,
            0x7FFFFFFFFFFFFF,
            id="half threshold not sampled",
        ),
        p(
            consistent_probability_based(0.5),
            False,
            None,
            0x80000000000000,
            True,
            0x80000000000000,
            0x80000000000000,
            id="half threshold sampled",
        ),
        p(
            consistent_probability_based(1.0),
            False,
            0x80000000000000,
            0x80000000000000,
            True,
            0,
            0x80000000000000,
            id="half threshold sampled",
        ),
    ),
)
def test_sample(
    sampler: Sampler,
    parent_sampled: bool,
    parent_threshold: Optional[int],
    parent_random_value: Optional[int],
    sampled: bool,
    threshold: float,
    random_value: float,
):
    parent_state = OtelTraceState.invalid()
    if parent_threshold is not None:
        parent_state.threshold = parent_threshold
    if parent_random_value is not None:
        parent_state.random_value = parent_random_value
    parent_state_str = parent_state.serialize()
    parent_trace_state = (
        TraceState((("ot", parent_state_str),)) if parent_state_str else None
    )
    flags = (
        TraceFlags(TraceFlags.SAMPLED)
        if parent_sampled
        else TraceFlags.get_default()
    )
    parent_span_context = SpanContext(
        TRACE_ID, SPAN_ID, False, flags, parent_trace_state
    )
    parent_span = NonRecordingSpan(parent_span_context)
    parent_context = set_span_in_context(parent_span)

    result = sampler.should_sample(
        parent_context, TRACE_ID, "name", trace_state=parent_trace_state
    )

    decision = Decision.RECORD_AND_SAMPLE if sampled else Decision.DROP
    state = OtelTraceState.parse(result.trace_state)

    assert result.decision == decision
    assert state.threshold == threshold
    assert state.random_value == random_value
