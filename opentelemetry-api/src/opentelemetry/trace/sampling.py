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

A `StaticSampler` always returns the same sampling decision regardless of the conditions. Both possible StaticSamplers are already created:

- Always sample spans: `ALWAYS_ON`
- Never sample spans: `ALWAYS_OFF`

A `ProbabilitySampler` makes a random sampling decision based on the sampling probability given. If the span being sampled has a parent, `ProbabilitySampler` will respect the parent span's sampling decision.

Currently, sampling decisions are always made during the creation of the span. However, this might not always be the case in the future (see `OTEP #115 <https://github.com/open-telemetry/oteps/pull/115>`_).

Custom samplers can be created by subclassing `Sampler` and implementing `Sampler.should_sample`.

To use a sampler, pass it into the tracer provider constructor. For example:

.. code:: python

    from opentelemetry import trace
    from opentelemetry.trace
    from opentelemetry.trace.sampling import ProbabilitySampler
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleExportSpanProcessor,
    )

    # sample 1 in every 1000 traces
    sampler = ProbabilitySampler(1/1000)

    # set the sampler onto the global tracer provider
    trace.set_tracer_provider(TracerProvider(sampler=sampler))

    # set up an exporter for sampled spans
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(ConsoleSpanExporter())
    )

    # created spans will now be sampled by the ProbabilitySampler
    with trace.get_tracer().start_as_current_span("Test Span"):
        ...
"""
import abc
from typing import Dict, Mapping, Optional, Sequence

# pylint: disable=unused-import
from opentelemetry.trace import Link, SpanContext
from opentelemetry.util.types import Attributes, AttributeValue


class Decision:
    """A sampling decision as applied to a newly-created Span.

    Args:
        sampled: Whether the `opentelemetry.trace.Span` should be sampled.
        attributes: Attributes to add to the `opentelemetry.trace.Span`.
    """

    def __repr__(self) -> str:
        return "{}({}, attributes={})".format(
            type(self).__name__, str(self.sampled), str(self.attributes)
        )

    def __init__(
        self,
        sampled: bool = False,
        attributes: Optional[Mapping[str, "AttributeValue"]] = None,
    ) -> None:
        self.sampled = sampled  # type: bool
        if attributes is None:
            self.attributes = {}  # type: Dict[str, "AttributeValue"]
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
        attributes: Optional[Attributes] = None,
        links: Sequence["Link"] = (),
    ) -> "Decision":
        pass


class StaticSampler(Sampler):
    """Sampler that always returns the same decision."""

    def __init__(self, decision: "Decision"):
        self._decision = decision

    def should_sample(
        self,
        parent_context: Optional["SpanContext"],
        trace_id: int,
        span_id: int,
        name: str,
        attributes: Optional[Attributes] = None,
        links: Sequence["Link"] = (),
    ) -> "Decision":
        return self._decision


class ProbabilitySampler(Sampler):
    """
    Sampler that makes sampling decisions probabalistically based on `rate`,
    while also respecting the parent span sampling decision.

    Args:
        rate: Probability (between 0 and 1) that a span will be sampled
    """

    def __init__(self, rate: float):
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
        span_id: int,
        name: str,
        attributes: Optional[Attributes] = None,  # TODO
        links: Sequence["Link"] = (),
    ) -> "Decision":
        if parent_context is not None:
            return Decision(parent_context.trace_flags.sampled)

        return Decision(trace_id & self.TRACE_ID_LIMIT < self.bound)


ALWAYS_OFF = StaticSampler(Decision(False))
"""Sampler that never samples spans, regardless of the parent span's sampling decision."""

ALWAYS_ON = StaticSampler(Decision(True))
"""Sampler that always samples spans, regardless of the parent span's sampling decision."""


DEFAULT_OFF = ProbabilitySampler(0.0)
"""Sampler that respects its parent span's sampling decision, but otherwise never samples."""

DEFAULT_ON = ProbabilitySampler(1.0)
"""Sampler that respects its parent span's sampling decision, but otherwise always samples."""
