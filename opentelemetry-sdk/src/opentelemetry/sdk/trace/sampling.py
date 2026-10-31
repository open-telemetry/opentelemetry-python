# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


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
    * traceidratio - Sampler that samples probabilistically based on rate.
    * parentbased_always_on - (default) Sampler that respects its parent span's sampling decision, but otherwise always samples.
    * parentbased_always_off - Sampler that respects its parent span's sampling decision, but otherwise never samples.
    * parentbased_traceidratio - Sampler that respects its parent span's sampling decision, but otherwise samples probabilistically based on rate.

Sampling probability can be set with ``OTEL_TRACES_SAMPLER_ARG`` if the sampler is traceidratio or parentbased_traceidratio. Rate must be in the range [0.0,1.0]. When not provided rate will be set to
1.0 (maximum rate possible).

A value of ``OTEL_TRACES_SAMPLER`` that is none of the six names above and matches no entry point
is logged as a warning and replaced by ``parentbased_always_on``. The four samplers that take no
rate ignore ``OTEL_TRACES_SAMPLER_ARG``: ``_get_from_env_or_default`` does not read the variable
for them at all, while the auto-configuration path does read it and hands the string to the
entry-point factory, which discards it. For ``traceidratio`` and
``parentbased_traceidratio`` it is parsed as a float. A value that does not parse, and a value
that parses but is outside [0.0, 1.0] or is NaN, are both logged as a warning and replaced by 1.0,
so neither one stops the SDK from starting.

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
        def get_sampler(sampler_argument):
            try:
                rate = float(sampler_argument)
                return CustomSampler(rate)
            except ValueError: # In case argument is empty string.
                return CustomSampler(0.5)

In order to configure you application with a custom sampler's entry point, set the ``OTEL_TRACES_SAMPLER`` environment variable to the key name of the entry point. For example, to configured the
above sampler, set ``OTEL_TRACES_SAMPLER=custom_sampler_name`` and ``OTEL_TRACES_SAMPLER_ARG=0.5``.
"""

from __future__ import annotations

import abc
import enum
import math
import os
from collections.abc import Sequence
from logging import getLogger
from types import MappingProxyType

# pylint: disable=unused-import
from opentelemetry.context import Context
from opentelemetry.sdk.environment_variables import (
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.trace import Link, SpanKind, get_current_span
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes

_logger = getLogger(__name__)


class Decision(enum.Enum):
    """What a sampler decided about one span.

    The decision controls two independent things: whether the SDK builds a
    recording span at all, and whether the sampled flag is set on the span
    context that is propagated to other processes.

    ``DROP`` produces a non-recording span, so its attributes, events and
    links are discarded and no processor sees it. ``RECORD_ONLY`` produces a
    recording span that processors see but whose sampled flag is clear, which
    both span processors in ``opentelemetry.sdk.trace.export`` use as a reason
    to skip it. ``RECORD_AND_SAMPLE`` produces a recording span with the
    sampled flag set.
    """

    # IsRecording() == false, span will not be recorded and all events and attributes will be dropped.
    DROP = 0
    # IsRecording() == true, but Sampled flag MUST NOT be set.
    RECORD_ONLY = 1
    # IsRecording() == true AND Sampled flag` MUST be set.
    RECORD_AND_SAMPLE = 2

    def is_recording(self):
        """Report whether the SDK should build a recording span.

        Returns:
            ``True`` for ``RECORD_ONLY`` and ``RECORD_AND_SAMPLE``, ``False``
            for ``DROP``.
        """
        return self in (Decision.RECORD_ONLY, Decision.RECORD_AND_SAMPLE)

    def is_sampled(self):
        """Report whether the sampled flag should be set on the span context.

        Returns:
            ``True`` only for ``RECORD_AND_SAMPLE``. ``RECORD_ONLY`` answers
            ``False`` even though the span is recorded.
        """
        return self is Decision.RECORD_AND_SAMPLE


class SamplingResult:
    """A sampling result as applied to a newly-created Span.

    ``attributes`` is wrapped in a read-only mapping when the instance is
    built, so nothing reached through ``SamplingResult.attributes`` can write
    to it, and ``None`` becomes an empty mapping rather than staying ``None``.
    The wrapper is a view and not a copy, so a sampler that keeps a reference
    to the dictionary it passed can still change what the result reports. The samplers in this module pass ``None`` whenever the decision
    is ``Decision.DROP``, which is why a dropped span never carries the
    attributes the caller asked for.

    Args:
        decision: A sampling decision based off of whether the span is recorded
            and the sampled flag in trace flags in the span context.
        attributes: Attributes to add to the `opentelemetry.trace.Span`.
        trace_state: The tracestate used for the `opentelemetry.trace.Span`.
            Could possibly have been modified by the sampler.
    """

    def __repr__(self) -> str:
        """Render the class name, the decision and the attributes.

        The trace state is left out, so two results that differ only in trace
        state have the same representation.

        Returns:
            A string such as ``SamplingResult(Decision.DROP, attributes={})``.
        """
        return f"{type(self).__name__}({self.decision!s}, attributes={self.attributes!s})"

    def __init__(
        self,
        decision: Decision,
        attributes: Attributes = None,
        trace_state: TraceState | None = None,
    ) -> None:
        """Build the result.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self.decision = decision
        if attributes is None:
            self.attributes = MappingProxyType({})
        else:
            self.attributes = MappingProxyType(attributes)
        self.trace_state = trace_state


class Sampler(abc.ABC):
    """Base class every sampler derives from.

    A subclass must implement both abstract methods. ``should_sample`` is
    called once per span, before the span object exists, so it can only see
    what is passed to it.
    """

    @abc.abstractmethod
    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Decide what should happen to a span that is about to be created.

        Args:
            parent_context: Context the span is being created in. ``None``
                means the currently active context, which is what makes a
                span with no explicit parent still pick one up.
            trace_id: Trace id the span will carry. For a root span this is a
                freshly generated id, for a child it is the trace id of the
                parent.
            name: Name the span is being created with. A sampler that reads
                it sees the name at creation time, and a later rename does
                not re-run sampling.
            kind: Span kind, or ``None`` when the caller did not give one.
            attributes: Attributes the caller passed at creation time. A
                sampler returns them, possibly changed, in the result.
            links: Links the caller passed at creation time, or ``None``.
            trace_state: Trace state the caller passed, or ``None``.
                Implementations are expected to take the trace state from
                ``parent_context`` instead and put it in the result.

        Returns:
            The decision, the attributes the span should start with, and the
            trace state the span context should carry.
        """

    @abc.abstractmethod
    def get_description(self) -> str:
        """Describe the sampler and its settings.

        The string identifies the configuration, not the instance, so two
        samplers built with the same arguments describe themselves the same
        way. It is what the SDK reports as the sampler in use.

        Returns:
            A description such as ``TraceIdRatioBased{0.001}``.
        """


class StaticSampler(Sampler):
    """Sampler that always returns the same decision.

    Nothing about the span is examined, so the trace id, the name, the kind
    and the parent make no difference. The two instances anyone normally
    needs already exist as ``ALWAYS_ON`` and ``ALWAYS_OFF``.

    Args:
        decision: Decision every call returns.
    """

    def __init__(self, decision: Decision) -> None:
        """Build the sampler.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._decision = decision

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Return the fixed decision.

        Args:
            parent_context: Context the span is being created in. Read only
                to copy the trace state of the parent into the result.
            trace_id: Ignored.
            name: Ignored.
            kind: Ignored.
            attributes: Returned as given, except under ``Decision.DROP``,
                where they are replaced by ``None`` and therefore discarded.
            links: Ignored.
            trace_state: Ignored. The trace state in the result comes from
                ``parent_context``.

        Returns:
            A result holding the fixed decision, the attributes, and the
            trace state of the parent, or ``None`` when there is no valid
            parent.
        """
        if self._decision is Decision.DROP:
            attributes = None
        return SamplingResult(
            self._decision,
            attributes,
            _get_parent_trace_state(parent_context),
        )

    def get_description(self) -> str:
        """Describe the sampler by the decision it was built with.

        Returns:
            ``"AlwaysOffSampler"`` under ``Decision.DROP``, and
            ``"AlwaysOnSampler"`` for both other decisions, so a sampler
            built with ``Decision.RECORD_ONLY`` describes itself as if it
            sampled.
        """
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

    The decision is a function of the trace id alone, with no randomness of
    its own, so every span of one trace gets the same answer and two SDKs
    configured with the same rate agree with each other. The 64 low-order
    bits of the trace id are compared against a bound computed once in the
    constructor as ``round(rate * 2 ** 64)``: the span is sampled when those
    bits are strictly less than the bound.

    A rate of 0.0 gives a bound of 0, and no trace id is below it, so nothing
    is sampled. A rate of 1.0 gives a bound of ``2 ** 64``, which every
    64-bit value is below, so everything is sampled. The accuracy of any rate
    in between depends on the 64 low-order bits of the trace id being
    uniformly distributed, which is what ``RandomIdGenerator`` provides.

    The parent is not consulted, so a child span can be sampled while its
    parent was dropped only if they carry different trace ids, which does not
    happen within one trace. Wrap this sampler in ``ParentBased`` to apply
    the rate to root spans alone.

    Args:
        rate: Probability (between 0 and 1) that a span will be sampled
    """

    def __init__(self, rate: float):
        """Build the sampler and compute its bound.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``rate`` is NaN or falls outside [0.0, 1.0].
        """
        if math.isnan(rate) or rate < 0.0 or rate > 1.0:
            raise ValueError("Probability must be in range [0.0, 1.0].")
        self._rate = rate
        self._bound = self.get_bound_for_rate(self._rate)

    # For compatibility with 64 bit trace IDs, the sampler checks the 64
    # low-order bits of the trace ID to decide whether to sample a given trace.
    TRACE_ID_LIMIT = (1 << 64) - 1

    @classmethod
    def get_bound_for_rate(cls, rate: float) -> int:
        """Convert a rate into the threshold the trace id is compared against.

        Args:
            rate: Probability in [0.0, 1.0]. The range is not checked here,
                so a value outside it yields a bound that no 64-bit trace id
                can reach, or one that every trace id is below.

        Returns:
            ``round(rate * 2 ** 64)``, the value a trace id must be strictly
            below to be sampled.
        """
        return round(rate * (cls.TRACE_ID_LIMIT + 1))

    @property
    def rate(self) -> float:
        """Probability this sampler was built with.

        Returns:
            The rate passed to the constructor, unchanged. It cannot be
            reassigned, so the bound can never fall out of step with it.
        """
        return self._rate

    @property
    def bound(self) -> int:
        """Threshold the 64 low-order bits of a trace id are compared against.

        Returns:
            The value computed from the rate in the constructor. A trace id
            whose 64 low-order bits are strictly below it is sampled.
        """
        return self._bound

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Compare the 64 low-order bits of the trace id against the bound.

        Args:
            parent_context: Context the span is being created in. Read only
                to copy the trace state of the parent into the result. The
                sampling decision of the parent is not consulted.
            trace_id: Trace id the span will carry. Only its 64 low-order
                bits are used, so the 64 high-order ones make no difference.
            name: Ignored.
            kind: Ignored.
            attributes: Returned as given when the span is sampled, and
                replaced by ``None`` when it is dropped.
            links: Ignored.
            trace_state: Ignored. The trace state in the result comes from
                ``parent_context``.

        Returns:
            A result holding ``Decision.RECORD_AND_SAMPLE`` when the trace id
            is below the bound and ``Decision.DROP`` otherwise, plus the
            attributes and the trace state of the parent.
        """
        decision = Decision.DROP
        if trace_id & self.TRACE_ID_LIMIT < self.bound:
            decision = Decision.RECORD_AND_SAMPLE
        if decision is Decision.DROP:
            attributes = None
        return SamplingResult(
            decision,
            attributes,
            _get_parent_trace_state(parent_context),
        )

    def get_description(self) -> str:
        """Describe the sampler by its rate.

        Returns:
            A string such as ``TraceIdRatioBased{0.001}``, built from the
            rate given to the constructor rather than from the bound.
        """
        return f"TraceIdRatioBased{{{self._rate}}}"


class ParentBased(Sampler):
    """
    If a parent is set, applies the respective delegate sampler.
    Otherwise, uses the root provided at initialization to make a
    decision.

    Exactly one of the five samplers handles any given span. ``root`` is used
    when the parent span context is missing or invalid, which is what a root
    span looks like. Otherwise two properties of the parent span context pick
    the delegate: whether it is remote, meaning it arrived in an incoming
    request rather than being created in this process, and whether its
    sampled flag is set. Remote and sampled selects
    ``remote_parent_sampled``, remote and not sampled selects
    ``remote_parent_not_sampled``, local and sampled selects
    ``local_parent_sampled``, and local and not sampled selects
    ``local_parent_not_sampled``.

    With the four defaults left alone, the sampler copies the decision of the
    parent and applies ``root`` only to root spans, which is the behaviour of
    ``DEFAULT_ON`` and ``DEFAULT_OFF``.

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
        """Build the sampler.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._root = root
        self._remote_parent_sampled = remote_parent_sampled
        self._remote_parent_not_sampled = remote_parent_not_sampled
        self._local_parent_sampled = local_parent_sampled
        self._local_parent_not_sampled = local_parent_not_sampled

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Pick a delegate from the parent span context and call it.

        Args:
            parent_context: Context the span is being created in. ``None``
                means the currently active context. The span context taken
                from it is what picks the delegate.
            trace_id: Trace id the span will carry. Passed to the delegate
                unchanged.
            name: Span name. Passed to the delegate unchanged.
            kind: Span kind, or ``None``. Passed to the delegate unchanged.
            attributes: Attributes given at creation time. Passed to the
                delegate unchanged.
            links: Links given at creation time, or ``None``. Passed to the
                delegate unchanged.
            trace_state: Accepted and not forwarded to the delegate, which
                therefore always sees ``None`` for it.

        Returns:
            Whatever the chosen delegate returns, unexamined and unchanged.
        """
        parent_span_context = get_current_span(parent_context).get_span_context()
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
        """Describe the sampler by the descriptions of all five delegates.

        Returns:
            A string such as
            ``ParentBased{root:AlwaysOnSampler,remoteParentSampled:...}``,
            naming each delegate in the order root, remote sampled, remote
            not sampled, local sampled, local not sampled.
        """
        return f"ParentBased{{root:{self._root.get_description()},remoteParentSampled:{self._remote_parent_sampled.get_description()},remoteParentNotSampled:{self._remote_parent_not_sampled.get_description()},localParentSampled:{self._local_parent_sampled.get_description()},localParentNotSampled:{self._local_parent_not_sampled.get_description()}}}"


class AlwaysRecordSampler(Sampler):
    """
    This sampler will return the sampling result of the provided `root`, unless the
    sampling result contains the sampling decision `Decision.DROP`, in which case, a
    new sampling result will be returned that is functionally equivalent to the original, except that
    it contains the sampling decision `Decision.RECORD_ONLY`. This ensures that all
    spans are recorded, with no change to sampling.

    The intended use case of this sampler is to provide a means of sending all spans to a
    processor without having an impact on the sampling rate. This may be desirable if a user wishes
    to count or otherwise measure all spans produced in a service, without incurring the cost of 100%
    sampling.

    Args:
        root: Sampler consulted for every span. Its result is passed through
            untouched unless it decided ``Decision.DROP``.
    """

    def __init__(self, root: Sampler):
        """Build the sampler.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``root`` is ``None``.
        """
        if root is None:
            raise ValueError("root must not be None")
        self._root = root

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Delegate to the root sampler and turn a drop into a record.

        Every argument is forwarded to the root sampler unchanged, including
        ``trace_state``, so the meaning of each one is whatever that sampler
        makes of it.

        Args:
            parent_context: Context the span is being created in, forwarded
                to the root sampler.
            trace_id: Trace id the span will carry, forwarded.
            name: Span name, forwarded.
            kind: Span kind, or ``None``, forwarded.
            attributes: Attributes given at creation time, forwarded.
            links: Links given at creation time, or ``None``, forwarded.
            trace_state: Trace state given at creation time, or ``None``,
                forwarded.

        Returns:
            The result of the root sampler when its decision is not
            ``Decision.DROP``. Otherwise a new result carrying
            ``Decision.RECORD_ONLY`` with the attributes and trace state the
            root sampler produced, which for the samplers in this module
            means an empty attribute mapping.
        """
        result: SamplingResult = self._root.should_sample(
            parent_context,
            trace_id,
            name,
            kind,
            attributes,
            links,
            trace_state,
        )
        if result.decision is Decision.DROP:
            result = SamplingResult(Decision.RECORD_ONLY, result.attributes, result.trace_state)

        return result

    def get_description(self):
        """Describe the sampler by the description of its root sampler.

        Returns:
            A string such as ``AlwaysRecordSampler{AlwaysOnSampler}``.
        """
        return f"AlwaysRecordSampler{{{self._root.get_description()}}}"


DEFAULT_OFF = ParentBased(ALWAYS_OFF)
"""Sampler that respects its parent span's sampling decision, but otherwise never samples."""

DEFAULT_ON = ParentBased(ALWAYS_ON)
"""Sampler that respects its parent span's sampling decision, but otherwise always samples."""


class ParentBasedTraceIdRatio(ParentBased):
    """
    Sampler that respects its parent span's sampling decision, but otherwise
    samples probabilistically based on `rate`.

    This is ``ParentBased`` with a ``TraceIdRatioBased`` root and the four
    parent delegates left at their defaults, so the rate applies to root
    spans alone and every child copies the decision of its parent.

    Args:
        rate: Probability in [0.0, 1.0] that a root span will be sampled.
    """

    def __init__(self, rate: float):
        """Build the root sampler from the rate and wrap it.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``rate`` is NaN or falls outside [0.0, 1.0]. The
                check happens in ``TraceIdRatioBased``.
        """
        root = TraceIdRatioBased(rate=rate)
        super().__init__(root=root)


class _AlwaysOff(StaticSampler):
    """Factory shape for the ``always_off`` value of ``OTEL_TRACES_SAMPLER``.

    ``_KNOWN_SAMPLERS`` maps that name to the ``ALWAYS_OFF`` instance rather
    than to this class, so nothing in this module constructs it. It exists so
    that code building a sampler from a name and an argument string has a
    callable with the same shape as ``TraceIdRatioBased``.

    Args:
        _: The sampler argument string. Accepted and discarded, since a
            static sampler has nothing to configure.
    """

    def __init__(self, _):
        """Build an always-off static sampler.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(Decision.DROP)


class _AlwaysOn(StaticSampler):
    """Factory shape for the ``always_on`` value of ``OTEL_TRACES_SAMPLER``.

    ``_KNOWN_SAMPLERS`` maps that name to the ``ALWAYS_ON`` instance rather
    than to this class, so nothing in this module constructs it.

    Args:
        _: The sampler argument string. Accepted and discarded.
    """

    def __init__(self, _):
        """Build an always-on static sampler.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(Decision.RECORD_AND_SAMPLE)


class _ParentBasedAlwaysOff(ParentBased):
    """Factory shape for the ``parentbased_always_off`` value of ``OTEL_TRACES_SAMPLER``.

    ``_KNOWN_SAMPLERS`` maps that name to the ``DEFAULT_OFF`` instance rather
    than to this class, so nothing in this module constructs it.

    Args:
        _: The sampler argument string. Accepted and discarded.
    """

    def __init__(self, _):
        """Build a parent-based sampler whose root never samples.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(ALWAYS_OFF)


class _ParentBasedAlwaysOn(ParentBased):
    """Factory shape for the ``parentbased_always_on`` value of ``OTEL_TRACES_SAMPLER``.

    ``_KNOWN_SAMPLERS`` maps that name to the ``DEFAULT_ON`` instance rather
    than to this class, so nothing in this module constructs it.

    Args:
        _: The sampler argument string. Accepted and discarded.
    """

    def __init__(self, _):
        """Build a parent-based sampler whose root always samples.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__(ALWAYS_ON)


_KNOWN_SAMPLERS = {
    "always_on": ALWAYS_ON,
    "always_off": ALWAYS_OFF,
    "parentbased_always_on": DEFAULT_ON,
    "parentbased_always_off": DEFAULT_OFF,
    "traceidratio": TraceIdRatioBased,
    "parentbased_traceidratio": ParentBasedTraceIdRatio,
}


def _get_from_env_or_default() -> Sampler:
    """Build the sampler named by ``OTEL_TRACES_SAMPLER``.

    The variable is lowercased and looked up in ``_KNOWN_SAMPLERS``. A name
    that is not there is logged as a warning and replaced by
    ``parentbased_always_on``, so a typo makes the SDK start with the default
    sampler instead of failing.

    ``OTEL_TRACES_SAMPLER_ARG`` is read only for ``traceidratio`` and
    ``parentbased_traceidratio``, and is parsed as a float. An unset or
    unparsable value and a value the sampler constructor rejects, meaning
    NaN or anything outside [0.0, 1.0], are handled the same way: a warning
    is logged and 1.0 is used. Entry-point samplers are resolved elsewhere,
    so a name registered under ``opentelemetry_traces_sampler`` does not
    reach this function.

    Returns:
        For the four names that take no rate, the shared module-level
        instance, meaning every caller gets the same object. For the two rate
        samplers, a new instance built with the parsed rate.
    """
    trace_sampler = os.getenv(OTEL_TRACES_SAMPLER, "parentbased_always_on").lower()
    if trace_sampler not in _KNOWN_SAMPLERS:
        _logger.warning("Couldn't recognize sampler %s.", trace_sampler)
        trace_sampler = "parentbased_always_on"

    if trace_sampler in ("traceidratio", "parentbased_traceidratio"):
        try:
            rate = float(os.getenv(OTEL_TRACES_SAMPLER_ARG, ""))
            return _KNOWN_SAMPLERS[trace_sampler](rate)
        except (ValueError, TypeError):
            _logger.warning("Could not convert TRACES_SAMPLER_ARG to float. Using default rate 1.0.")
            return _KNOWN_SAMPLERS[trace_sampler](1.0)

    return _KNOWN_SAMPLERS[trace_sampler]


def _get_parent_trace_state(
    parent_context: Context | None,
) -> TraceState | None:
    """Pull the trace state of the parent out of a context.

    Used by the samplers in this module to fill the trace state of their
    result, so that vendor entries set upstream survive into the new span.

    Args:
        parent_context: Context the span is being created in. ``None`` means
            the currently active context.

    Returns:
        The trace state of the parent span context, or ``None`` when that
        context is missing or invalid, which is the case for a root span.
    """
    parent_span_context = get_current_span(parent_context).get_span_context()
    if parent_span_context is None or not parent_span_context.is_valid:
        return None
    return parent_span_context.trace_state
