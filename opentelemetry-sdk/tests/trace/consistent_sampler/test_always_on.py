from opentelemetry.sdk.trace._sampling_experimental import consistent_always_on
from opentelemetry.sdk.trace.sampling import Decision

from .testutil import random_trace_id


def test_description():
    assert (
        consistent_always_on().get_description() == "ConsistentAlwaysOnSampler"
    )


def test_threshold():
    assert (
        consistent_always_on()
        .sampling_intent(None, "test", None, {}, None, None)
        .threshold
        == 0
    )


def test_sampling():
    sampler = consistent_always_on()

    num_sampled = 0
    for _ in range(10000):
        res = sampler.should_sample(
            None, random_trace_id(), "span", None, None, None, None
        )
        if res.decision == Decision.RECORD_AND_SAMPLE:
            num_sampled += 1
            assert res.trace_state is not None
            assert res.trace_state.get("ot", "") == "th:0"

    assert num_sampled == 10000
