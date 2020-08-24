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

"""
For general information about sampling, see `the specification <https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/sdk.md#sampling>`_.

OpenTelemetry provides two types of samplers:

- `StaticSampler`
- `ProbabilitySampler`

A `StaticSampler` always returns the same sampling result regardless of the conditions. Both possible StaticSamplers are already created:

- Always sample spans: ALWAYS_ON
- Never sample spans: `ALWAYS_OFF`

A `ProbabilitySampler` makes a random sampling result based on the sampling probability given.

If the span being sampled has a parent, `ParentOrElse` will respect the parent span's sampling result. Otherwise, it returns the sampling result from the given delegate sampler.

Currently, sampling results are always made during the creation of the span. However, this might not always be the case in the future (see `OTEP #115 <https://github.com/open-telemetry/oteps/pull/115>`_).

Custom samplers can be created by subclassing `Sampler` and implementing `Sampler.should_sample`.

To use a sampler, pass it into the tracer provider constructor. For example:

.. code:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleExportSpanProcessor,
    )
    from opentelemetry.sdk.trace.sampling import ProbabilitySampler

    # sample 1 in every 1000 traces
    sampler = ProbabilitySampler(1/1000)

    # set the sampler onto the global tracer provider
    trace.set_tracer_provider(TracerProvider(sampler=sampler))

    # set up an exporter for sampled spans
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(ConsoleSpanExporter())
    )

    # created spans will now be sampled by the ProbabilitySampler
    with trace.get_tracer(__name__).start_as_current_span("Test Span"):
        ...
"""
import abc
import enum
from typing import Dict, Mapping, Optional, Sequence

# pylint: disable=unused-import
from opentelemetry.trace import Link, SpanContext
from opentelemetry.util.types import Attributes, AttributeValue


class Decision(enum.Enum):
    # IsRecording() == false, span will not be recorded and all events and attributes will be dropped.
    NOT_RECORD = 0
    # IsRecording() == true, but Sampled flag MUST NOT be set.
    RECORD = 1
    # IsRecording() == true AND Sampled flag` MUST be set.
    RECORD_AND_SAMPLED = 2


def is_recording(decision: Decision):
    return decision in (Decision.RECORD, Decision.RECORD_AND_SAMPLED)


def is_sampled(decision: Decision):
    return decision is Decision.RECORD_AND_SAMPLED


class SamplingResult:
    """A sampling result as applied to a newly-created Span.

    Args:
        decision: A sampling decision based off of whether the span is recorded
            and the sampled flag in trace flags in the span context.
        attributes: Attributes to add to the `opentelemetry.trace.Span`.
    """

    def __repr__(self) -> str:
        return "{}({}, attributes={})".format(
            type(self).__name__, str(self.decision), str(self.attributes)
        )

    def __init__(
        self,
        decision: Decision,
        attributes: Optional[Mapping[str, "AttributeValue"]] = None,
    ) -> None:
        self.decision = decision
        # TODO: attributes must be immutable
        if attributes is None:
            self.attributes = {}  # type: Dict[str, "AttributeValue"]
        else:
            self.attributes = attributes


class Sampler(abc.ABC):
    @abc.abstractmethod
    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        name: str,
        attributes: Attributes = None,
        links: Sequence["Link"] = (),
    ) -> "SamplingResult":
        pass

    @abc.abstractmethod
    def get_description(self) -> str:
        pass


class StaticSampler(Sampler):
    """Sampler that always returns the same decision."""

    def __init__(self, decision: "Decision"):
        self._decision = decision

    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        name: str,
        attributes: Attributes = None,
        links: Sequence["Link"] = (),
    ) -> "SamplingResult":
        if self._decision is Decision.NOT_RECORD:
            return SamplingResult(self._decision)
        return SamplingResult(self._decision, attributes)

    def get_description(self) -> str:
        if self._decision is Decision.NOT_RECORD:
            return "AlwaysOffSampler"
        return "AlwaysOnSampler"


class ProbabilitySampler(Sampler):
    """
    Sampler that makes sampling decisions probabalistically based on `rate`,
    while also respecting the parent span sampling decision.

    Args:
        rate: Probability (between 0 and 1) that a span will be sampled
    """

    def __init__(self, rate: float):
        if rate < 0.0 or rate > 1.0:
            raise ValueError("Probability must be in range [0.0, 1.0].")
        self._rate = rate
        self._bound = self.get_bound_for_rate(self._rate)

    # For compatibility with 64 bit trace IDs, the sampler checks the 64
    # low-order bits of the trace ID to decide whether to sample a given trace.
    TRACE_ID_LIMIT = (1 << 64) - 1

    @classmethod
    def get_bound_for_rate(cls, rate: float) -> int:
        return round(rate * (cls.TRACE_ID_LIMIT + 1))

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
        name: str,
        attributes: Attributes = None,  # TODO
        links: Sequence["Link"] = (),
    ) -> "SamplingResult":
        decision = Decision.NOT_RECORD
        if trace_id & self.TRACE_ID_LIMIT < self.bound:
            decision = Decision.RECORD_AND_SAMPLED
        if decision is Decision.NOT_RECORD:
            return SamplingResult(decision)
        return SamplingResult(decision, attributes)

    def get_description(self) -> str:
        return "ProbabilitySampler{{{}}}".format(self._rate)


class ParentOrElse(Sampler):
    """
    If a parent is set, follows the same sampling decision as the parent.
    Otherwise, uses the delegate provided at initialization to make a
    decision.

    Args:
        delegate: The delegate sampler to use if parent is not set.
    """

    def __init__(self, delegate: Sampler):
        self._delegate = delegate

    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        name: str,
        attributes: Attributes = None,  # TODO
        links: Sequence["Link"] = (),
    ) -> "SamplingResult":
        if parent_context is not None:
            if (
                not parent_context.is_valid()
                or not parent_context.trace_flags.sampled
            ):
                return SamplingResult(Decision.NOT_RECORD)
            return SamplingResult(Decision.RECORD_AND_SAMPLED, attributes)

        return self._delegate.should_sample(
            parent_context=parent_context,
            trace_id=trace_id,
            name=name,
            attributes=attributes,
            links=links,
        )

    def get_description(self):
        return "ParentOrElse{{{}}}".format(self._delegate.get_description())


ALWAYS_OFF = StaticSampler(Decision.NOT_RECORD)
"""Sampler that never samples spans, regardless of the parent span's sampling decision."""

ALWAYS_ON = StaticSampler(Decision.RECORD_AND_SAMPLED)
"""Sampler that always samples spans, regardless of the parent span's sampling decision."""

DEFAULT_OFF = ParentOrElse(ALWAYS_OFF)
"""Sampler that respects its parent span's sampling decision, but otherwise never samples."""

DEFAULT_ON = ParentOrElse(ALWAYS_ON)
"""Sampler that respects its parent span's sampling decision, but otherwise always samples."""
