from dataclasses import dataclass
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


@dataclass
class Input:
    sampler: Sampler
    sampled: bool
    threshold: Optional[int]
    random_value: Optional[int]


@dataclass
class Output:
    sampled: bool
    threshold: int
    random_value: int


@pytest.mark.parametrize(
    "input,output",
    (
        p(
            Input(
                sampler=consistent_always_on(),
                sampled=True,
                threshold=None,
                random_value=None,
            ),
            Output(
                sampled=True, threshold=0, random_value=INVALID_RANDOM_VALUE
            ),
            id="min threshold no parent random value",
        ),
        p(
            Input(
                sampler=consistent_always_on(),
                sampled=True,
                threshold=None,
                random_value=0x7F99AA40C02744,
            ),
            Output(sampled=True, threshold=0, random_value=0x7F99AA40C02744),
            id="min threshold with parent random value",
        ),
        p(
            Input(
                sampler=consistent_always_off(),
                sampled=True,
                threshold=None,
                random_value=None,
            ),
            Output(
                sampled=False,
                threshold=INVALID_THRESHOLD,
                random_value=INVALID_RANDOM_VALUE,
            ),
            id="max threshold",
        ),
        p(
            Input(
                sampler=consistent_parent_based(consistent_always_on()),
                sampled=False,
                threshold=0x7F99AA40C02744,
                random_value=0x7F99AA40C02744,
            ),
            Output(
                sampled=True,
                threshold=0x7F99AA40C02744,
                random_value=0x7F99AA40C02744,
            ),
            id="parent based in consistent mode",
        ),
        p(
            Input(
                sampler=consistent_parent_based(consistent_always_on()),
                sampled=True,
                threshold=None,
                random_value=None,
            ),
            Output(
                sampled=True,
                threshold=INVALID_THRESHOLD,
                random_value=INVALID_RANDOM_VALUE,
            ),
            id="parent based in legacy mode",
        ),
        p(
            Input(
                sampler=consistent_probability_based(0.5),
                sampled=True,
                threshold=None,
                random_value=0x7FFFFFFFFFFFFF,
            ),
            Output(
                sampled=False,
                threshold=INVALID_THRESHOLD,
                random_value=0x7FFFFFFFFFFFFF,
            ),
            id="half threshold not sampled",
        ),
        p(
            Input(
                sampler=consistent_probability_based(0.5),
                sampled=False,
                threshold=None,
                random_value=0x80000000000000,
            ),
            Output(
                sampled=True,
                threshold=0x80000000000000,
                random_value=0x80000000000000,
            ),
            id="half threshold sampled",
        ),
        p(
            Input(
                sampler=consistent_probability_based(1.0),
                sampled=False,
                threshold=0x80000000000000,
                random_value=0x80000000000000,
            ),
            Output(sampled=True, threshold=0, random_value=0x80000000000000),
            id="half threshold sampled",
        ),
    ),
)
def test_sample(input: Input, output: Output):
    parent_state = OtelTraceState.invalid()
    if input.threshold is not None:
        parent_state.threshold = input.threshold
    if input.random_value is not None:
        parent_state.random_value = input.random_value
    parent_state_str = parent_state.serialize()
    parent_trace_state = (
        TraceState((("ot", parent_state_str),)) if parent_state_str else None
    )
    flags = (
        TraceFlags(TraceFlags.SAMPLED)
        if input.sampled
        else TraceFlags.get_default()
    )
    parent_span_context = SpanContext(
        TRACE_ID, SPAN_ID, False, flags, parent_trace_state
    )
    parent_span = NonRecordingSpan(parent_span_context)
    parent_context = set_span_in_context(parent_span)

    result = input.sampler.should_sample(
        parent_context, TRACE_ID, "name", trace_state=parent_trace_state
    )

    decision = Decision.RECORD_AND_SAMPLE if output.sampled else Decision.DROP
    state = OtelTraceState.parse(result.trace_state)

    assert result.decision == decision
    assert state.threshold == output.threshold
    assert state.random_value == output.random_value
