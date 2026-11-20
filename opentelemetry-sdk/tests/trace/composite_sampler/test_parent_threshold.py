# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from opentelemetry.sdk.trace._sampling_experimental import composable_always_on, composable_parent_threshold
from opentelemetry.sdk.trace._sampling_experimental._util import INVALID_THRESHOLD, MIN_THRESHOLD
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState, set_span_in_context


@pytest.mark.parametrize("explicit_randomness", [False, True])
@pytest.mark.parametrize(
    "sampled,randomness,threshold,reliable",
    [
        (True, 0x80000000000000, 0x80000000000000, True),
        (True, 0x7FFFFFFFFFFFFF, MIN_THRESHOLD, False),
        (False, 0x80000000000000, INVALID_THRESHOLD, False),
        (False, 0x7FFFFFFFFFFFFF, 0x80000000000000, True),
    ],
)
def test_parent_threshold_consistency(
    sampled: bool, randomness: int, threshold: int, reliable: bool, explicit_randomness: bool
) -> None:
    ot = "th:8"
    if explicit_randomness:
        ot += f";rv:{randomness:014x}"
    trace_state = TraceState([("ot", ot)])
    # When explicit randomness is present, use a trace ID that would yield the opposite decision.
    trace_id = (1 << 64) | (randomness ^ (1 << 55) if explicit_randomness else randomness)
    parent = NonRecordingSpan(
        SpanContext(trace_id, 1, True, TraceFlags(TraceFlags.SAMPLED if sampled else 0), trace_state)
    )
    intent = composable_parent_threshold(composable_always_on()).sampling_intent(
        set_span_in_context(parent), "child", None, None, None, trace_state
    )
    assert intent.threshold == threshold
    assert intent.threshold_reliable is reliable
