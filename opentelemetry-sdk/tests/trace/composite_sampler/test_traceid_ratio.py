# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from opentelemetry.sdk.trace._sampling_experimental import (
    composable_traceid_ratio_based,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._trace_state import (
    OtelTraceState,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import Decision


@pytest.mark.parametrize(
    ("ratio", "threshold"),
    (
        (1.0, "0"),
        (0.5, "8"),
        (0.25, "c"),
        (1e-300, "max"),
        (0, "max"),
    ),
)
def test_description(ratio: float, threshold: str):
    assert (
        composable_traceid_ratio_based(ratio).get_description()
        == f"ComposableTraceIDRatioBased{{threshold={threshold}, ratio={ratio}}}"
    )


@pytest.mark.parametrize(
    ("ratio", "threshold"),
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
def test_sampling(ratio: float, threshold: int):
    sampler = composite_sampler(composable_traceid_ratio_based(ratio))

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
            otts = OtelTraceState.parse(res.trace_state)
            assert otts.threshold == threshold
            assert otts.random_value == -1

    expected_num_sampled = int(10000 * ratio)
    assert abs(num_sampled - expected_num_sampled) < 50
