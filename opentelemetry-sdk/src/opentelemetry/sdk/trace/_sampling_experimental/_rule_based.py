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

from typing import Protocol, Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import AnyValue, Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._util import INVALID_THRESHOLD


class PredicateT(Protocol):
    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool: ...

    def __str__(self) -> str: ...


class AttributePredicate:
    """An exact match of an attribute value"""

    def __init__(self, key: str, value: AnyValue):
        self.key = key
        self.value = value

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        if not attributes:
            return False
        return attributes.get(self.key) == self.value

    def __str__(self):
        return f"{self.key}={self.value}"


RulesT = Sequence[tuple[PredicateT, ComposableSampler]]

_non_sampling_intent = SamplingIntent(
    threshold=INVALID_THRESHOLD, threshold_reliable=False
)


class _ComposableRuleBased(ComposableSampler):
    def __init__(self, rules: RulesT):
        # work on an internal copy of the rules
        self._rules = list(rules)

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None = None,
    ) -> SamplingIntent:
        for predicate, sampler in self._rules:
            if predicate(
                parent_ctx=parent_ctx,
                name=name,
                span_kind=span_kind,
                attributes=attributes,
                links=links,
                trace_state=trace_state,
            ):
                return sampler.sampling_intent(
                    parent_ctx=parent_ctx,
                    name=name,
                    span_kind=span_kind,
                    attributes=attributes,
                    links=links,
                    trace_state=trace_state,
                )
        return _non_sampling_intent

    def get_description(self) -> str:
        rules_str = ",".join(
            f"({predicate}:{sampler.get_description()})"
            for predicate, sampler in self._rules
        )
        return f"ComposableRuleBased{{[{rules_str}]}}"


def composable_rule_based(
    rules: RulesT,
) -> ComposableSampler:
    """Returns a consistent sampler that:

    - Evaluates a series of rules based on predicates and returns the SamplingIntent from the first matching sampler
    - If no rules match, returns a non-sampling intent

    Args:
        rules: A list of (Predicate, ComposableSampler) pairs, where Predicate is a function that evaluates whether a rule applies
    """
    return _ComposableRuleBased(rules)
