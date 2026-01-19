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
    composable_always_on,
    composable_rule_based,
    composite_sampler,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import Decision


def _rule_name_is_foo(
    parent_ctx,
    name,
    span_kind,
    attributes,
    links,
    trace_state,
):
    return name == "foo"


def test_description():
    assert (
        composable_rule_based(rules=[]).get_description()
        == "ComposableRuleBased"
    )


def test_sampling_intent_match():
    rules = [
        (_rule_name_is_foo, composable_always_on()),
    ]
    assert (
        composable_rule_based(rules=rules)
        .sampling_intent(None, "foo", None, {}, None, None)
        .threshold
        == 0
    )


def test_sampling_intent_no_match():
    rules = [
        (_rule_name_is_foo, composable_always_on()),
    ]
    assert (
        composable_rule_based(rules=rules)
        .sampling_intent(None, "test", None, {}, None, None)
        .threshold
        == -1
    )


def test_should_sample_match():
    rules = [
        (_rule_name_is_foo, composable_always_on()),
    ]
    sampler = composite_sampler(composable_rule_based(rules=rules))

    res = sampler.should_sample(
        None,
        RandomIdGenerator().generate_trace_id(),
        "foo",
        None,
        None,
        None,
        None,
    )

    assert res.decision == Decision.RECORD_AND_SAMPLE
    assert res.trace_state is not None
    assert res.trace_state.get("ot", "") == "th:0"


def test_should_sample_no_match():
    rules = [
        (_rule_name_is_foo, composable_always_on()),
    ]
    sampler = composite_sampler(composable_rule_based(rules=rules))

    res = sampler.should_sample(
        None,
        RandomIdGenerator().generate_trace_id(),
        "test",
        None,
        None,
        None,
        None,
    )

    assert res.decision == Decision.DROP
    assert res.trace_state is None
