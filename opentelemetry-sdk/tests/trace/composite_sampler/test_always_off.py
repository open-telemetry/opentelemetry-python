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
