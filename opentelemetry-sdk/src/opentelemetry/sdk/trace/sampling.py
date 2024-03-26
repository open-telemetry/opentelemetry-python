# Copyright The OpenTelemetry Authors
# Copyright (c) 2016 Uber Technologies, Inc.
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
For general information about sampling, see `the specification <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md#sampling>`_.

OpenTelemetry provides two types of samplers:

- `StaticSampler`
- `TraceIdRatioBased`

A `StaticSampler` always returns the same sampling result regardless of the conditions. Both possible StaticSamplers are already created:

- Always sample spans: ALWAYS_ON
- Never sample spans: ALWAYS_OFF

A `TraceIdRatioBased` sampler makes a random sampling result based on the sampling probability given.

If the span being sampled has a parent, `ParentBased` will respect the parent delegate sampler. Otherwise, it returns the sampling result from the given root sampler.

Currently, sampling results are always made during the creation of the span. However, this might not always be the case in the future (see `OTEP #115 <https://github.com/open-telemetry/oteps/pull/115>`_).

Custom samplers can be created by subclassing `Sampler` and implementing `Sampler.should_sample` as well as `Sampler.get_description`.

Samplers are able to modify the `opentelemetry.trace.span.TraceState` of the parent of the span being created. For custom samplers, it is suggested to implement `Sampler.should_sample` to utilize the
parent span context's `opentelemetry.trace.span.TraceState` and pass into the `SamplingResult` instead of the explicit trace_state field passed into the parameter of `Sampler.should_sample`.

To use a sampler, pass it into the tracer provider constructor. For example:

.. code:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    # sample 1 in every 1000 traces
    sampler = TraceIdRatioBased(1/1000)

    # set the sampler onto the global tracer provider
    trace.set_tracer_provider(TracerProvider(sampler=sampler))

    # set up an exporter for sampled spans
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

    # created spans will now be sampled by the TraceIdRatioBased sampler
    with trace.get_tracer(__name__).start_as_current_span("Test Span"):
        ...

The tracer sampler can also be configured via environment variables ``OTEL_TRACES_SAMPLER`` and ``OTEL_TRACES_SAMPLER_ARG`` (only if applicable).
The list of built-in values for ``OTEL_TRACES_SAMPLER`` are:

    * always_on - Sampler that always samples spans, regardless of the parent span's sampling decision.
    * always_off - Sampler that never samples spans, regardless of the parent span's sampling decision.
    * traceidratio - Sampler that samples probabalistically based on rate.
    * parentbased_always_on - (default) Sampler that respects its parent span's sampling decision, but otherwise always samples.
    * parentbased_always_off - Sampler that respects its parent span's sampling decision, but otherwise never samples.
    * parentbased_traceidratio - Sampler that respects its parent span's sampling decision, but otherwise samples probabalistically based on rate.

Sampling probability can be set with ``OTEL_TRACES_SAMPLER_ARG`` if the sampler is traceidratio or parentbased_traceidratio. Rate must be in the range [0.0,1.0]. When not provided rate will be set to
1.0 (maximum rate possible).

Prev example but with environment variables. Please make sure to set the env ``OTEL_TRACES_SAMPLER=traceidratio`` and ``OTEL_TRACES_SAMPLER_ARG=0.001``.

.. code:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    trace.set_tracer_provider(TracerProvider())

    # set up an exporter for sampled spans
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

    # created spans will now be sampled by the TraceIdRatioBased sampler with rate 1/1000.
    with trace.get_tracer(__name__).start_as_current_span("Test Span"):
        ...

When utilizing a configurator, you can configure a custom sampler. In order to create a configurable custom sampler, create an entry point for the custom sampler
factory method or function under the entry point group, ``opentelemetry_traces_sampler``. The custom sampler factory method must be of type ``Callable[[str], Sampler]``, taking a single string argument and
returning a Sampler object. The single input will come from the string value of the ``OTEL_TRACES_SAMPLER_ARG`` environment variable. If ``OTEL_TRACES_SAMPLER_ARG`` is not configured, the input will
be an empty string. For example:

.. code:: python

    setup(
        ...
        entry_points={
            ...
            "opentelemetry_traces_sampler": [
                "custom_sampler_name = path.to.sampler.factory.method:CustomSamplerFactory.get_sampler"
            ]
        }
    )
    # ...
    class CustomRatioSampler(Sampler):
        def __init__(rate):
            # ...
    # ...
    class CustomSamplerFactory:
        @staticmethod
        get_sampler(sampler_argument):
            try:
                rate = float(sampler_argument)
                return CustomSampler(rate)
            except ValueError: # In case argument is empty string.
                return CustomSampler(0.5)

In order to configure you application with a custom sampler's entry point, set the ``OTEL_TRACES_SAMPLER`` environment variable to the key name of the entry point. For example, to configured the
above sampler, set ``OTEL_TRACES_SAMPLER=custom_sampler_name`` and ``OTEL_TRACES_SAMPLER_ARG=0.5``.


TODO(sconover): Need good explanation here if/when the overall approach 
(porting of python jaeger remote sampler code) meets with approval
"""
import abc
import asyncio
import enum
import json
import os
import random
import threading
from logging import getLogger
from tornado.ioloop import PeriodicCallback
from types import MappingProxyType
from typing import Any, Dict, Optional, Sequence

# pylint: disable=unused-import
from opentelemetry.context import Context
from opentelemetry.sdk.environment_variables import (
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.trace import Link, SpanKind, get_current_span
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes

from opentelemetry.sdk.trace import rate_limiter

_logger = getLogger(__name__)

# TODO(sconover): not sure what to do w/ these constants + associated attrs, 
# the don't seem like a "fit" in this codebase. However these are central to the workings
# of the ported tests.
SAMPLER_TYPE_TAG_KEY = 'sampler.type'
SAMPLER_PARAM_TAG_KEY = 'sampler.param'

SAMPLER_TYPE_RATE_LIMITING = 'ratelimiting'
SAMPLER_TYPE_LOWER_BOUND = 'lowerbound'
SAMPLER_TYPE_TRACE_ID_RATIO = 'traceidratio'
SAMPLER_TYPE_PARENT_BASED_TRACE_ID_RATIO = 'parentbased_traceidratio'
SAMPLER_TYPE_GUARANTEED_THROUGHPUT = 'guaranteedthroughput'
SAMPLER_TYPE_ADAPTIVE = 'adaptive'
SAMPLER_TYPE_REMOTE_CONTROLLED = 'remotecontrolled'

# How often remotely controlled sampler polls for sampling strategy
DEFAULT_SAMPLING_INTERVAL = 60


DEFAULT_SAMPLING_PROBABILITY = 0.001
DEFAULT_LOWER_BOUND = 1.0 / (10.0 * 60.0)  # sample once every 10 minutes
DEFAULT_MAX_OPERATIONS = 2000

STRATEGIES_STR = 'perOperationStrategies'
OPERATION_STR = 'operation'
DEFAULT_LOWER_BOUND_STR = 'defaultLowerBoundTracesPerSecond'
PROBABILISTIC_SAMPLING_STR = 'probabilisticSampling'
SAMPLING_RATE_STR = 'samplingRate'
DEFAULT_SAMPLING_PROBABILITY_STR = 'defaultSamplingProbability'
OPERATION_SAMPLING_STR = 'operationSampling'
MAX_TRACES_PER_SECOND_STR = 'maxTracesPerSecond'
RATE_LIMITING_SAMPLING_STR = 'rateLimitingSampling'
STRATEGY_TYPE_STR = 'strategyType'
PROBABILISTIC_SAMPLING_STRATEGY = 'PROBABILISTIC'
RATE_LIMITING_SAMPLING_STRATEGY = 'RATE_LIMITING'

class Decision(enum.Enum):
    # IsRecording() == false, span will not be recorded and all events and attributes will be dropped.
    DROP = 0
    # IsRecording() == true, but Sampled flag MUST NOT be set.
    RECORD_ONLY = 1
    # IsRecording() == true AND Sampled flag` MUST be set.
    RECORD_AND_SAMPLE = 2

    def is_recording(self):
        return self in (Decision.RECORD_ONLY, Decision.RECORD_AND_SAMPLE)

    def is_sampled(self):
        return self is Decision.RECORD_AND_SAMPLE


class SamplingResult:
    """A sampling result as applied to a newly-created Span.

    Args:
        decision: A sampling decision based off of whether the span is recorded
            and the sampled flag in trace flags in the span context.
        attributes: Attributes to add to the `opentelemetry.trace.Span`.
        trace_state: The tracestate used for the `opentelemetry.trace.Span`.
            Could possibly have been modified by the sampler.
    """

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self.decision)}, attributes={str(self.attributes)})"

    def __init__(
        self,
        decision: Decision,
        attributes: "Attributes" = None,
        trace_state: Optional["TraceState"] = None,
    ) -> None:
        self.decision = decision
        if attributes is None:
            self.attributes = MappingProxyType({})
        else:
            self.attributes = MappingProxyType(attributes)
        self.trace_state = trace_state


class Sampler(abc.ABC):
    @abc.abstractmethod
    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        pass

    @abc.abstractmethod
    def get_description(self) -> str:
        pass

    # TODO(sconover) added close to all samplers, because of cleanup needed
    # for RemoteControlledSampler
    # Q: Where should sampler.close() be called? I believe it might be 
    # TracerProvider#shutdown (but not entirely sure)
    def close(self) -> None:
        pass

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, self.__class__) and self.__dict__ == other.__dict__
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

class StaticSampler(Sampler):
    """Sampler that always returns the same decision."""

    def __init__(self, decision: "Decision") -> None:
        self._decision = decision

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        if self._decision is Decision.DROP:
            attributes = None
        return SamplingResult(
            self._decision,
            attributes,
            _get_parent_trace_state(parent_context),
        )

    def get_description(self) -> str:
        if self._decision is Decision.DROP:
            return "AlwaysOffSampler"
        return "AlwaysOnSampler"


ALWAYS_OFF = StaticSampler(Decision.DROP)
"""Sampler that never samples spans, regardless of the parent span's sampling decision."""

ALWAYS_ON = StaticSampler(Decision.RECORD_AND_SAMPLE)
"""Sampler that always samples spans, regardless of the parent span's sampling decision."""


class TraceIdRatioBased(Sampler):
    """
    Sampler that makes sampling decisions probabilistically based on `rate`.

    Args:
        rate: Probability (between 0 and 1) that a span will be sampled
    """

    def __init__(self, rate: float):
        if rate < 0.0 or rate > 1.0:
            raise ValueError("Probability must be in range [0.0, 1.0].")
        self._rate = rate
        self._bound = self.get_bound_for_rate(self._rate)
        self._attributes = {
            SAMPLER_TYPE_TAG_KEY: SAMPLER_TYPE_TRACE_ID_RATIO,
            SAMPLER_PARAM_TAG_KEY: rate
        }

    # For compatibility with 64 bit trace IDs, the sampler checks the 64
    # low-order bits of the trace ID to decide whether to sample a given trace.
    TRACE_ID_LIMIT = (1 << 64) - 1

    @classmethod
    def get_bound_for_rate(cls, rate: float) -> int:
        return round(rate * (cls.TRACE_ID_LIMIT + 1))

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def bound(self) -> int:
        return self._bound

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        decision = Decision.DROP
        if trace_id & self.TRACE_ID_LIMIT < self.bound:
            decision = Decision.RECORD_AND_SAMPLE
        if decision is Decision.DROP:
            attributes = None
        
        # TODO(sconover): the jaeger tests really really want this probabilistic sampler to indicate
        # key elements of internal state via attributes
        if attributes == None:
            attributes = {}
        attributes = {**self._attributes, **attributes}
        
        return SamplingResult(
            decision,
            attributes,
            _get_parent_trace_state(parent_context),
        )

    def get_description(self) -> str:
        return f"TraceIdRatioBased{{{self._rate}}}"

    def __str__(self) -> str:
        return self.get_description()

class ParentBased(Sampler):
    """
    If a parent is set, applies the respective delegate sampler.
    Otherwise, uses the root provided at initialization to make a
    decision.

    Args:
        root: Sampler called for spans with no parent (root spans).
        remote_parent_sampled: Sampler called for a remote sampled parent.
        remote_parent_not_sampled: Sampler called for a remote parent that is
            not sampled.
        local_parent_sampled: Sampler called for a local sampled parent.
        local_parent_not_sampled: Sampler called for a local parent that is
            not sampled.
    """

    def __init__(
        self,
        root: Sampler,
        remote_parent_sampled: Sampler = ALWAYS_ON,
        remote_parent_not_sampled: Sampler = ALWAYS_OFF,
        local_parent_sampled: Sampler = ALWAYS_ON,
        local_parent_not_sampled: Sampler = ALWAYS_OFF,
    ):
        self._root = root
        self._remote_parent_sampled = remote_parent_sampled
        self._remote_parent_not_sampled = remote_parent_not_sampled
        self._local_parent_sampled = local_parent_sampled
        self._local_parent_not_sampled = local_parent_not_sampled

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        parent_span_context = get_current_span(
            parent_context
        ).get_span_context()
        # default to the root sampler
        sampler = self._root
        # respect the sampling and remote flag of the parent if present
        if parent_span_context is not None and parent_span_context.is_valid:
            if parent_span_context.is_remote:
                if parent_span_context.trace_flags.sampled:
                    sampler = self._remote_parent_sampled
                else:
                    sampler = self._remote_parent_not_sampled
            else:
                if parent_span_context.trace_flags.sampled:
                    sampler = self._local_parent_sampled
                else:
                    sampler = self._local_parent_not_sampled

        return sampler.should_sample(
            parent_context=parent_context,
            trace_id=trace_id,
            name=name,
            kind=kind,
            attributes=attributes,
            links=links,
        )

    def get_description(self):
        return f"ParentBased{{root:{self._root.get_description()},remoteParentSampled:{self._remote_parent_sampled.get_description()},remoteParentNotSampled:{self._remote_parent_not_sampled.get_description()},localParentSampled:{self._local_parent_sampled.get_description()},localParentNotSampled:{self._local_parent_not_sampled.get_description()}}}"


DEFAULT_OFF = ParentBased(ALWAYS_OFF)
"""Sampler that respects its parent span's sampling decision, but otherwise never samples."""

DEFAULT_ON = ParentBased(ALWAYS_ON)
"""Sampler that respects its parent span's sampling decision, but otherwise always samples."""


class ParentBasedTraceIdRatio(ParentBased):
    """
    Sampler that respects its parent span's sampling decision, but otherwise
    samples probabalistically based on `rate`.
    """

    def __init__(self, rate: float):
        root = TraceIdRatioBased(rate=rate)
        super().__init__(root=root)


class _AlwaysOff(StaticSampler):
    def __init__(self, _):
        super().__init__(Decision.DROP)


class _AlwaysOn(StaticSampler):
    def __init__(self, _):
        super().__init__(Decision.RECORD_AND_SAMPLE)


class _ParentBasedAlwaysOff(ParentBased):
    def __init__(self, _):
        super().__init__(ALWAYS_OFF)


class _ParentBasedAlwaysOn(ParentBased):
    def __init__(self, _):
        super().__init__(ALWAYS_ON)

class RateLimitingSampler(Sampler):
    """
    Samples at most max_traces_per_second. The distribution of sampled
    traces follows burstiness of the service, i.e. a service with uniformly
    distributed requests will have those requests sampled uniformly as well,
    but if requests are bursty, especially sub-second, then a number of
    sequential requests can be sampled each second.
    """

    def __init__(self, max_traces_per_second: float = 10) -> None:
        self.rate_limiter: rate_limiter.RateLimiter = None  # type:ignore  # value is set below
        self._init(max_traces_per_second)

    def _init(self, max_traces_per_second: float):
        assert max_traces_per_second >= 0, \
            'max_traces_per_second must not be negative'
        self._attributes = {
            SAMPLER_TYPE_TAG_KEY: SAMPLER_TYPE_RATE_LIMITING,
            SAMPLER_PARAM_TAG_KEY: max_traces_per_second,
        }
        self.traces_per_second = max_traces_per_second
        max_balance = max(self.traces_per_second, 1.0)
        if not self.rate_limiter:
            self.rate_limiter = rate_limiter.RateLimiter(
                credits_per_second=self.traces_per_second,
                max_balance=max_balance
            )
        else:
            self.rate_limiter.update(max_traces_per_second, max_balance)

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        decision = Decision.DROP
        if self.rate_limiter.check_credit(1.0):
            decision = Decision.RECORD_AND_SAMPLE
        
        # TODO(sconover): what's the idea w/ override attributes (passed in above)?
        # should these be merged with self._attributes?

        return SamplingResult(
            decision,
            self._attributes,
            _get_parent_trace_state(parent_context),
        )

    def __eq__(self, other) -> bool:
        """The last_tick and balance fields can be different"""
        if not isinstance(other, self.__class__):
            return False
        d1 = dict(self.rate_limiter.__dict__)
        d2 = dict(other.rate_limiter.__dict__)
        d1['balance'] = d2['balance']
        d1['last_tick'] = d2['last_tick']
        return d1 == d2

    def update(self, max_traces_per_second: float) -> bool:
        if self.traces_per_second == max_traces_per_second:
            return False
        self._init(max_traces_per_second)
        return True
    
    def get_description(self) -> str:
        return f'RateLimitingSampler{{{self.traces_per_second}}}'

    def __str__(self) -> str:
        return self.get_description()

class GuaranteedThroughputProbabilisticSampler(Sampler):
    """
    A sampler that leverages both TraceIdRatioBased sampler and RateLimitingSampler.
    The RateLimitingSampler is used as a guaranteed lower bound sampler such
    that every operation is sampled at least once in a time interval defined by
    the lower_bound. ie a lower_bound of 1.0 / (60 * 10) will sample an
    operation at least once every 10 minutes.

    The TraceIdRatioBased sampler is given higher priority when attributes are emitted,
    ie. if is_sampled() for both samplers return true, the attributes for
    TraceIdRatioBased sampler will be used.
    """
    def __init__(self, operation: str, lower_bound: float, rate: float) -> None:
        self._attributes = {
            SAMPLER_TYPE_TAG_KEY: SAMPLER_TYPE_LOWER_BOUND,
            SAMPLER_PARAM_TAG_KEY: rate,
        }
        self.probabilistic_sampler = TraceIdRatioBased(rate)
        self.lower_bound_sampler = RateLimitingSampler(lower_bound)
        self.operation = operation
        self.rate = rate
        self.lower_bound = lower_bound

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":
        
        # TODO(sconover): what's the idea w/ override attributes (passed in above)?
        # should these be merged with self._attributes?

        sample_result = \
            self.probabilistic_sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
        if sample_result.decision.is_sampled():
            self.lower_bound_sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
            return SamplingResult(
                Decision.RECORD_AND_SAMPLE,
                # TODO(sconover) re-evaluate all of these sampler attrs from jaeger...
                # how useful are they? can we delete them (and accompanying test assertions)?
                {
                    SAMPLER_TYPE_TAG_KEY: SAMPLER_TYPE_TRACE_ID_RATIO,
                    SAMPLER_PARAM_TAG_KEY: self.probabilistic_sampler.rate,
                },
                _get_parent_trace_state(parent_context),
            )
        sample_result = self.lower_bound_sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
        return SamplingResult(
            sample_result.decision,
            self._attributes,
            _get_parent_trace_state(parent_context),
        )

    def update(self, lower_bound: int, rate: float) -> None:
        # (NB) This function should only be called while holding a Write lock.
        if self.rate != rate:
            self.probabilistic_sampler = TraceIdRatioBased(rate)
            self.rate = rate
            self._attributes = {
                SAMPLER_TYPE_TAG_KEY: SAMPLER_TYPE_LOWER_BOUND,
                SAMPLER_PARAM_TAG_KEY: rate,
            }
        if self.lower_bound != lower_bound:
            self.lower_bound_sampler.update(lower_bound)
            self.lower_bound = lower_bound

    def get_description(self) -> str:
        return f'GuaranteedThroughputProbabilisticSampler{{{self.operation}, {self.rate}, {self.lower_bound}}}'

    def __str__(self) -> str:
        return self.get_description()

class AdaptiveSampler(Sampler):
    """
    A sampler that leverages both TraceIdRatioBased sampler and RateLimitingSampler
    via the GuaranteedThroughputProbabilisticSampler. This sampler keeps track
    of all operations and delegates calls the the respective
    GuaranteedThroughputProbabilisticSampler.
    """
    def __init__(self, strategies: Dict[str, Any], max_operations: int) -> None:
        samplers = {}
        for strategy in strategies.get(STRATEGIES_STR, []):
            operation = strategy.get(OPERATION_STR)
            sampler = GuaranteedThroughputProbabilisticSampler(
                operation,
                strategies.get(DEFAULT_LOWER_BOUND_STR, DEFAULT_LOWER_BOUND),
                get_sampling_probability(strategy)
            )
            samplers[operation] = sampler

        self.samplers = samplers
        self.default_sampler = \
            TraceIdRatioBased(strategies.get(DEFAULT_SAMPLING_PROBABILITY_STR,
                                             DEFAULT_SAMPLING_PROBABILITY))
        self.default_sampling_probability = \
            strategies.get(DEFAULT_SAMPLING_PROBABILITY_STR, DEFAULT_SAMPLING_PROBABILITY)
        self.lower_bound = strategies.get(DEFAULT_LOWER_BOUND_STR, DEFAULT_LOWER_BOUND)
        self.max_operations = max_operations

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional["TraceState"] = None,
    ) -> "SamplingResult":        
        sampler = self.samplers.get(name)
        if not sampler:
            if len(self.samplers) >= self.max_operations:
                return self.default_sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
            sampler = GuaranteedThroughputProbabilisticSampler(
                name,
                self.lower_bound,
                self.default_sampling_probability
            )
            self.samplers[name] = sampler
            return sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)
        return sampler.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)

    def update(self, strategies: Dict[str, Any]) -> None:
        # (NB) This function should only be called while holding a Write lock.
        for strategy in strategies.get(STRATEGIES_STR, []):
            operation = strategy.get(OPERATION_STR)
            lower_bound = strategies.get(DEFAULT_LOWER_BOUND_STR, DEFAULT_LOWER_BOUND)
            sampling_rate = get_sampling_probability(strategy)
            sampler = self.samplers.get(operation)
            if not sampler:
                sampler = GuaranteedThroughputProbabilisticSampler(
                    operation,
                    lower_bound,
                    sampling_rate
                )
                self.samplers[operation] = sampler
            else:
                sampler.update(lower_bound, sampling_rate)
        self.lower_bound = strategies.get(DEFAULT_LOWER_BOUND_STR, DEFAULT_LOWER_BOUND)
        if self.default_sampling_probability != strategies.get(DEFAULT_SAMPLING_PROBABILITY_STR,
                                                               DEFAULT_SAMPLING_PROBABILITY):
            self.default_sampling_probability = \
                strategies.get(DEFAULT_SAMPLING_PROBABILITY_STR, DEFAULT_SAMPLING_PROBABILITY)
            self.default_sampler = \
                TraceIdRatioBased(self.default_sampling_probability)

    def close(self) -> None:
        for _, sampler in self.samplers.items():
            sampler.close()

    def get_description(self) -> str:
        return f'AdaptiveSampler{{{self.default_sampling_probability}, {self.lower_bound}, {self.max_operations}}}'

    def __str__(self) -> str:
        return self.get_description()

class RemoteControlledSampler(Sampler):
    """Periodically loads the sampling strategy from a remote server."""
    def __init__(self, channel: Any, service_name: str, **kwargs: Any) -> None:
        """
        :param channel: channel for communicating with jaeger-agent-compatible source
        :param service_name: name of this application
        :param kwargs: optional parameters
            - init_sampler: initial value of the sampler,
                else TraceIdRatioBased(0.001)
            - sampling_refresh_interval: interval in seconds for polling
              for new strategy
            - logger: Logger instance
            # TODO(sconover) there's a general question about what to do about metrics...
            # - metrics: metrics facade, used to emit metrics on errors.
            #     This parameter has been deprecated, please use
            #     metrics_factory instead.
            # - metrics_factory: used to generate metrics for errors
            - error_reporter: ErrorReporter instance
            - max_operations: maximum number of unique operations the
              AdaptiveSampler will keep track of
        :param init:
        :return:
        """
        self._channel = channel
        self.service_name = service_name
        self.logger = kwargs.get('logger', _logger)
        self.sampler = kwargs.get('init_sampler')
        self.sampling_refresh_interval = \
            kwargs.get('sampling_refresh_interval') or DEFAULT_SAMPLING_INTERVAL
        # TODO(sconover) there's a general question about what to do about metrics...
        # self.metrics_factory = kwargs.get('metrics_factory') \
        #     or LegacyMetricsFactory(kwargs.get('metrics') or Metrics())
        # self.metrics = SamplerMetrics(self.metrics_factory)
        self.error_reporter = kwargs.get('error_reporter')
        # TODO(sconover) what should we do about making/using a real error reporter?
        #or \
        #   ErrorReporter(Metrics())
        self.max_operations = kwargs.get('max_operations') or \
            DEFAULT_MAX_OPERATIONS

        if not self.sampler:
            self.sampler = TraceIdRatioBased(DEFAULT_SAMPLING_PROBABILITY)
        else:
            self.sampler.should_sample(None, 0, "span name").decision.is_sampled() # assert we got valid sampler API

        self.lock = threading.Lock()
        self.running = True
        self.periodic = None

        self.io_loop = channel.io_loop
        if not self.io_loop:
            self.logger.error(
                'Cannot acquire IOLoop, sampler will not be updated')
        else:
            # according to IOLoop docs, it's not safe to use timeout methods
            # unless already running in the loop, so we use `add_callback`
            self.io_loop.add_callback(self._init_polling)

    def should_sample(
        self,
        *args,
    ) -> "SamplingResult":
        with self.lock:
            assert self.sampler  # needed for mypy
            return self.sampler.should_sample(*args)
        
    def _init_polling(self):
        """
        Bootstrap polling for sampling strategy.

        To avoid spiky traffic from the samplers, we use a random delay
        before the first poll.
        """
        with self.lock:
            if not self.running:
                return
            r = random.Random()
            delay = r.random() * self.sampling_refresh_interval
            self.io_loop.call_later(delay=delay,
                                    callback=self._delayed_polling)
            self.logger.info(
                'Delaying sampling strategy polling by %d sec', delay)

    def _delayed_polling(self):
        periodic = self._create_periodic_callback()
        self._poll_sampling_manager()  # Initialize sampler now
        with self.lock:
            if not self.running:
                return
            self.periodic = periodic
            periodic.start()  # start the periodic cycle
            self.logger.info(
                'Tracing sampler started with sampling refresh '
                'interval %d sec', self.sampling_refresh_interval)

    def _create_periodic_callback(self):
        return PeriodicCallback(
            callback=self._poll_sampling_manager,
            # convert interval to milliseconds
            callback_time=self.sampling_refresh_interval * 1000)

    def _sampling_request_callback(self, future):
        exception = future.exception()
        if exception:
            # TODO(sconover) there's a general question about what to do about metrics...
            # self.metrics.sampler_query_failure(1)
            self.error_reporter.error(
                'Fail to get sampling strategy from jaeger-agent: %s',
                exception)
            return

        response = future.result()

        # TODO(sconover) should we eliminate all pre-py3.5-ish code?
        # In Python 3.5 response.body is of type bytes and json.loads() does only support str
        # See: https://github.com/jaegertracing/jaeger-client-python/issues/180
        if hasattr(response.body, 'decode') and callable(response.body.decode):
            response_body = response.body.decode('utf-8')
        else:
            response_body = response.body

        try:
            sampling_strategies_response = json.loads(response_body)
            # TODO(sconover) there's a general question about what to do about metrics...
            # self.metrics.sampler_retrieved(1)
        except Exception as e:
            # TODO(sconover) there's a general question about what to do about metrics...
            # self.metrics.sampler_query_failure(1)
            self.error_reporter.error(
                'Fail to parse sampling strategy '
                'from jaeger-agent: %s [%s]', e, response_body)
            return

        self._update_sampler(sampling_strategies_response)
        self.logger.debug('Tracing sampler set to %s', self.sampler)

    def _update_sampler(self, response):
        with self.lock:
            try:
                if response.get(OPERATION_SAMPLING_STR):
                    self._update_adaptive_sampler(response.get(OPERATION_SAMPLING_STR))
                else:
                    self._update_rate_limiting_or_probabilistic_sampler(response)
            except Exception as e:
                # TODO(sconover) there's a general question about what to do about metrics...
                # self.metrics.sampler_update_failure(1)
                self.error_reporter.error(
                    'Fail to update sampler'
                    'from jaeger-agent: %s [%s]', e, response)
    
    def _update_adaptive_sampler(self, per_operation_strategies):
        if isinstance(self.sampler, AdaptiveSampler):
            self.sampler.update(per_operation_strategies)
        else:
            self.sampler = AdaptiveSampler(per_operation_strategies, self.max_operations)
        # TODO(sconover) there's a general question about what to do about metrics...
        # self.metrics.sampler_updated(1)

    def _update_rate_limiting_or_probabilistic_sampler(self, response):
        s_type = response.get(STRATEGY_TYPE_STR)
        new_sampler = self.sampler
        if s_type == PROBABILISTIC_SAMPLING_STRATEGY:
            sampling_rate = get_sampling_probability(response)
            new_sampler = TraceIdRatioBased(rate=sampling_rate)
        elif s_type == RATE_LIMITING_SAMPLING_STRATEGY:
            mtps = get_rate_limit(response)
            if mtps < 0 or mtps >= 500:
                raise ValueError(
                    'Rate limiting parameter not in [0, 500) range: %s' % mtps)
            if isinstance(self.sampler, RateLimitingSampler):
                if self.sampler.update(max_traces_per_second=mtps):
                    pass
                    # TODO(sconover) there's a general question about what to do about metrics...
                    # self.metrics.sampler_updated(1)
            else:
                new_sampler = RateLimitingSampler(max_traces_per_second=mtps)
        else:
            raise ValueError('Unsupported sampling strategy type: %s' % s_type)

        if self.sampler != new_sampler:
            self.sampler = new_sampler
            # TODO(sconover) there's a general question about what to do about metrics...
            # self.metrics.sampler_updated(1)

    def _poll_sampling_manager(self):
        self.logger.debug('Requesting tracing sampler refresh')
        fut = self._channel.request_sampling_strategy(self.service_name)
        fut.add_done_callback(self._sampling_request_callback)

    def close(self) -> None:
        with self.lock:
            self.running = False
            if self.periodic:
                self.periodic.stop()

    def get_description(self) -> str:
        return f'RateLimitingSampler{{{self.traces_per_second}}}'

    def __str__(self) -> str:
        return self.get_description()
    
def get_sampling_probability(strategy: Optional[Dict[str, Any]] = None) -> float:
    if not strategy:
        return DEFAULT_SAMPLING_PROBABILITY
    probability_strategy = strategy.get(PROBABILISTIC_SAMPLING_STR)
    if not probability_strategy:
        return DEFAULT_SAMPLING_PROBABILITY
    return probability_strategy.get(SAMPLING_RATE_STR, DEFAULT_SAMPLING_PROBABILITY)

def get_rate_limit(strategy: Optional[Dict[str, Any]] = None) -> float:
    if not strategy:
        return DEFAULT_LOWER_BOUND
    rate_limit_strategy = strategy.get(RATE_LIMITING_SAMPLING_STR)
    if not rate_limit_strategy:
        return DEFAULT_LOWER_BOUND
    return rate_limit_strategy.get(MAX_TRACES_PER_SECOND_STR, DEFAULT_LOWER_BOUND)

_KNOWN_SAMPLERS = {
    "always_on": ALWAYS_ON,
    "always_off": ALWAYS_OFF,
    "parentbased_always_on": DEFAULT_ON,
    "parentbased_always_off": DEFAULT_OFF,
    SAMPLER_TYPE_TRACE_ID_RATIO: TraceIdRatioBased,
    SAMPLER_TYPE_PARENT_BASED_TRACE_ID_RATIO: ParentBasedTraceIdRatio,
    SAMPLER_TYPE_RATE_LIMITING: RateLimitingSampler,
    SAMPLER_TYPE_GUARANTEED_THROUGHPUT: GuaranteedThroughputProbabilisticSampler,
    SAMPLER_TYPE_ADAPTIVE: AdaptiveSampler,
    SAMPLER_TYPE_REMOTE_CONTROLLED: RemoteControlledSampler,
}


def _get_from_env_or_default() -> Sampler:
    trace_sampler = os.getenv(
        OTEL_TRACES_SAMPLER, "parentbased_always_on"
    ).lower()
    if trace_sampler not in _KNOWN_SAMPLERS:
        _logger.warning("Couldn't recognize sampler %s.", trace_sampler)
        trace_sampler = "parentbased_always_on"

    if trace_sampler in ("traceidratio", "parentbased_traceidratio"):
        try:
            rate = float(os.getenv(OTEL_TRACES_SAMPLER_ARG))
        except (ValueError, TypeError):
            _logger.warning("Could not convert TRACES_SAMPLER_ARG to float.")
            rate = 1.0
        return _KNOWN_SAMPLERS[trace_sampler](rate)

    return _KNOWN_SAMPLERS[trace_sampler]


def _get_parent_trace_state(
    parent_context: Optional[Context],
) -> Optional["TraceState"]:
    parent_span_context = get_current_span(parent_context).get_span_context()
    if parent_span_context is None or not parent_span_context.is_valid:
        return None
    return parent_span_context.trace_state
