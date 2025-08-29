# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pytest import param as p

from opentelemetry.sdk.trace._sampling_experimental import (
    ComposableSampler,
    composable_always_off,
    composable_always_on,
    composable_parent_threshold,
    composable_traceid_ratio_based,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._trace_state import (
    OtelTraceState,
)
from opentelemetry.sdk.trace._sampling_experimental._util import (
    INVALID_RANDOM_VALUE,
    INVALID_THRESHOLD,
)
from opentelemetry.sdk.trace.sampling import Decision
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
    sampler: ComposableSampler
    sampled: bool
    threshold: int | None
    random_value: int | None


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
                sampler=composable_always_on(),
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
                sampler=composable_always_on(),
                sampled=True,
                threshold=None,
                random_value=0x7F99AA40C02744,
            ),
            Output(sampled=True, threshold=0, random_value=0x7F99AA40C02744),
            id="min threshold with parent random value",
        ),
        p(
            Input(
                sampler=composable_always_off(),
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
                sampler=composable_parent_threshold(composable_always_on()),
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
                sampler=composable_parent_threshold(composable_always_on()),
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
                sampler=composable_traceid_ratio_based(0.5),
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
                sampler=composable_traceid_ratio_based(0.5),
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
                sampler=composable_traceid_ratio_based(1.0),
                sampled=False,
                threshold=0x80000000000000,
                random_value=0x80000000000000,
            ),
            Output(sampled=True, threshold=0, random_value=0x80000000000000),
            id="parent violating invariant",
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

    result = composite_sampler(input.sampler).should_sample(
        parent_context, TRACE_ID, "name", trace_state=parent_trace_state
    )

    decision = Decision.RECORD_AND_SAMPLE if output.sampled else Decision.DROP
    state = OtelTraceState.parse(result.trace_state)

    assert result.decision == decision
    assert state.threshold == output.threshold
    assert state.random_value == output.random_value
