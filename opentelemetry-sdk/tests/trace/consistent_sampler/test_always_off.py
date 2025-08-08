from opentelemetry.sdk.trace._sampling_experimental import (
    consistent_always_off,
)
from opentelemetry.sdk.trace.sampling import Decision

from .testutil import random_trace_id


def test_description():
    assert (
        consistent_always_off().get_description()
        == "ConsistentAlwaysOffSampler"
    )


def test_threshold():
    assert (
        consistent_always_off()
        .sampling_intent(None, "test", None, {}, None, None)
        .threshold
        == -1
    )


def test_sampling():
    sampler = consistent_always_off()

    num_sampled = 0
    for _ in range(10000):
        res = sampler.should_sample(
            None, random_trace_id(), "span", None, None, None, None
        )
        if res.decision == Decision.RECORD_AND_SAMPLE:
            num_sampled += 1
        assert not res.trace_state

    assert num_sampled == 0
