# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.trace._sampling_experimental import (
    composable_always_off,
    composite_sampler,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import Decision


def test_description():
    assert composable_always_off().get_description() == "ComposableAlwaysOff"


def test_threshold():
    assert (
        composable_always_off()
        .sampling_intent(None, "test", None, {}, None, None)
        .threshold
        == -1
    )


def test_sampling():
    sampler = composite_sampler(composable_always_off())

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
        assert not res.trace_state

    assert num_sampled == 0
