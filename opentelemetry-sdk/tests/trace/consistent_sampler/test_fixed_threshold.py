import pytest

from opentelemetry.sdk.trace._sampling_experimental import (
    consistent_probability_based,
)
from opentelemetry.sdk.trace._sampling_experimental._trace_state import (
    OtelTraceState,
)
from opentelemetry.sdk.trace.sampling import Decision

from .testutil import random_trace_id


@pytest.mark.parametrize(
    "probability,threshold",
    (
        (1.0, "0"),
        (0.5, "8"),
        (0.25, "c"),
        (1e-300, "max"),
        (0, "max"),
    ),
)
def test_description(probability: float, threshold: str):
    assert (
        consistent_probability_based(probability).get_description()
        == f"ConsistentFixedThresholdSampler{{threshold={threshold}, sampling probability={probability}}}"
    )


@pytest.mark.parametrize(
    "probability,threshold",
    (
        (1.0, 0),
        (0.5, 36028797018963968),
        (0.25, 54043195528445952),
        (0.125, 63050394783186944),
        (0.0, 72057594037927936),
        (0.45, 39631676720860364),
        (0.2, 57646075230342348),
        (0.13, 62690106812997304),
        (0.05, 68454714336031539),
    ),
)
def test_sampling(probability: float, threshold: int):
    sampler = consistent_probability_based(probability)

    num_sampled = 0
    for _ in range(10000):
        res = sampler.should_sample(
            None, random_trace_id(), "span", None, None, None, None
        )
        if res.decision == Decision.RECORD_AND_SAMPLE:
            num_sampled += 1
            assert res.trace_state is not None
            otts = OtelTraceState.parse(res.trace_state)
            assert otts.threshold == threshold
            assert otts.random_value == -1

    expected_num_sampled = int(10000 * probability)
    assert abs(num_sampled - expected_num_sampled) < 50
