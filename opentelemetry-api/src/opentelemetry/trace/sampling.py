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

    def __repr__(self):
        return "{}({}, attributes={})".format(
            type(self).__name__, self.sampled, self.attributes
        )

    def __init__(
        self,
        sampled: bool = False,
        attributes: Mapping[str, "AttributeValue"] = None,
    ) -> None:
        self.sampled = sampled
        if attributes is None:
            self.attributes = {}  # type:Dict[str, "AttributeValue"]
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


ALWAYS_OFF = StaticSampler(Decision(False))
ALWAYS_ON = StaticSampler(Decision(True))
