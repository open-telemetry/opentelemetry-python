# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.trace._sampling_experimental import (
    composable_always_on,
    composite_sampler,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import Decision


def test_description():
    assert composable_always_on().get_description() == "ComposableAlwaysOn"


def test_threshold():
    assert (
        composable_always_on()
        .sampling_intent(None, "test", None, {}, None, None)
        .threshold
        == 0
    )


def test_sampling():
    sampler = composite_sampler(composable_always_on())

    num_sampled = 0
    for _ in range(10000):
        res = sampler.should_sample(
            None,
            RandomIdGenerator().generate_trace_id(),
            "span",
            None,
            None,
            None,
            None,
        )
        if res.decision == Decision.RECORD_AND_SAMPLE:
            num_sampled += 1
            assert res.trace_state is not None
            assert res.trace_state.get("ot", "") == "th:0"

    assert num_sampled == 10000
