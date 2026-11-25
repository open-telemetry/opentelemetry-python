# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A sampler that records the arguments the SDK passes to it.

A sampling decision is taken before a span exists, from the name, kind and
attributes handed to ``start_span``. Instrumentation that sets an attribute
after the span has started leaves a sampler unable to see it, which is a
regression a test cannot detect by inspecting the finished span.
:class:`CapturingSampler` makes it detectable by keeping what it was given.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState, get_current_span
from opentelemetry.util.types import Attributes, AttributeValue


class CapturingSampler(Sampler):
    """Sampler that records what the SDK passes to ``should_sample``.

    Instrumentation tests use it to assert which span kind and attributes a
    sampler can see when a span starts, for example request headers that have
    to be available for sampling decisions.

    Every span is recorded and sampled unless ``required_attributes`` is given,
    in which case a span is dropped when any of these attributes is missing or
    has a different value.

    After a span has started, ``name``, ``kind`` and ``attributes`` hold what
    the SDK passed for the most recent sampling decision, and are ``None``,
    ``None`` and an empty dict before the first one.

    Args:
        required_attributes: Attributes a span has to carry at start time to be
            sampled, compared by equality. ``None`` or an empty mapping samples
            every span. The mapping is copied, so later edits to the argument do
            not change the sampling decisions.
    """

    name: str | None
    kind: SpanKind | None
    attributes: dict[str, AttributeValue]

    def __init__(self, required_attributes: Attributes = None) -> None:
        """Parameters are documented on the class docstring."""
        self.required_attributes = dict(required_attributes or {})
        self.name = None
        self.kind = None
        self.attributes = {}

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
        """Record the sampling arguments and decide whether to sample.

        Only the last call is kept, so a test that starts several spans sees
        the arguments of the last one.

        Args:
            parent_context: Context the new span is starting in. Its current
                span supplies the trace state carried into the result. ``None``
                means the current context.
            trace_id: Trace id of the new span. Ignored by this sampler, so the
                decision does not vary across traces.
            name: Name the span is starting with, recorded as ``self.name``.
            kind: Kind the span is starting with, recorded as ``self.kind``.
            attributes: Attributes passed at span start, copied into
                ``self.attributes``. Copied rather than stored, so attributes
                set after the span starts cannot make a missing one look
                present. ``None`` is recorded as an empty dict.
            links: Links of the new span. Ignored by this sampler.
            trace_state: Trace state proposed for the new span. Ignored: the
                result carries the trace state of the parent instead.

        Returns:
            A ``SamplingResult`` with ``RECORD_AND_SAMPLE`` when every entry of
            ``required_attributes`` is present in ``attributes`` with the same
            value, and ``DROP`` otherwise. A dropped span carries no attributes
            in the result. The trace state of the parent span is carried over
            when the parent context is valid, and is ``None`` when there is no
            valid parent.
        """
        self.name = name
        self.kind = kind
        # Snapshot now so attributes set after span creation cannot hide a regression.
        self.attributes = dict(attributes or {})

        decision = Decision.RECORD_AND_SAMPLE
        if any(
            key not in self.attributes or self.attributes[key] != value
            for key, value in self.required_attributes.items()
        ):
            decision = Decision.DROP
            attributes = None

        parent_span_context = get_current_span(parent_context).get_span_context()
        return SamplingResult(
            decision,
            attributes,
            parent_span_context.trace_state if parent_span_context.is_valid else None,
        )

    def get_description(self) -> str:
        """Return the human-readable description of this sampler.

        The SDK uses a sampler description only when a composite sampler such
        as ``ParentBased`` builds its own description out of the samplers it
        wraps. Nothing attaches it to a span, so a test cannot assert on it
        through exported telemetry.

        Returns:
            The constant ``"CapturingSampler"``. It does not vary with
            ``required_attributes``, so two instances configured differently
            describe themselves identically.
        """
        return "CapturingSampler"
