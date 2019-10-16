# Copyright 2019, OpenTelemetry Authors
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

import abc
from typing import Dict, Mapping, Optional, Sequence

# pylint: disable=unused-import
from opentelemetry.trace import Link, SpanContext
from opentelemetry.util.types import AttributeValue


class Decision:
    """A sampling decision as applied to a newly-created Span.

    Args:
        sampled: Whether the `Span` should be sampled.
        attributes: Attributes to add to the `Span`.
    """

    def __repr__(self) -> str:
        return "{}({}, attributes={})".format(
            type(self).__name__,
            str(self.sampled),
            str(self.attributes)
        )

    def __init__(
        self,
        sampled: bool = False,
        attributes: Mapping[str, "AttributeValue"] = None,
    ) -> None:
        self.sampled: bool
        self.attributes: Dict[str, "AttributeValue"]

        self.sampled = sampled
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = dict(attributes)


class Sampler(abc.ABC):
    @abc.abstractmethod
    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        span_id: int,
        name: str,
        links: Optional[Sequence["Link"]] = None,
    ) -> "Decision":
        pass


class StaticSampler(Sampler):
    """Sampler that always returns the same decision."""

    def __init__(self, decision: "Decision"):
        self.decision = decision

    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        span_id: int,
        name: str,
        links: Optional[Sequence["Link"]] = None,
    ) -> "Decision":
        return self.decision


class ProbabilitySampler(Sampler):
    def __init__(self, rate: float):
        self._rate = rate
        self._bound = self.get_bound_for_rate(self._rate)

    @classmethod
    def get_bound_for_rate(cls, rate: float) -> int:
        return int(rate * 0xffffffffffffffff)

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, new_rate: float) -> None:
        self._rate = new_rate
        self._bound = self.get_bound_for_rate(self._rate)

    @property
    def bound(self) -> int:
        return self._bound

    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        span_id: int,
        name: str,
        links: Optional[Sequence["Link"]] = None,
    ) -> "Decision":
        if parent_context is not None:
            return Decision(parent_context.trace_options.recorded, {})

        return Decision(trace_id & 0xffffffffffffffff <= self.bound, {})

# Samplers that ignore the parent sampling decision and never/always sample.
ALWAYS_OFF = StaticSampler(Decision(False))
ALWAYS_ON = StaticSampler(Decision(True))

# Samplers that respect the parent sampling decision, but otherwise
# never/always sample.
DEFAULT_OFF = ProbabilitySampler(0.0)
DEFAULT_ON = ProbabilitySampler(1.0)
