# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The interface every composable sampler in this subpackage implements.

A composable sampler answers one question about a span that is about to be
created: which sampling threshold applies to it. It never decides whether the
span is sampled. That comparison belongs to the composite sampler built by
``composite_sampler``, which reads the randomness value, compares it against
the threshold and produces the ``SamplingResult``. Splitting the work this way
is what lets samplers be nested, as ``composable_rule_based`` and
``composable_parent_threshold`` do, without any of them having to agree on how
randomness is obtained.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes


@dataclass(frozen=True)
class SamplingIntent:
    """Information to make a consistent sampling decision.

    The instance is frozen. Several samplers in this subpackage build one
    intent at import or construction time and hand back the same object for
    every span, while ``_ComposableParentThreshold`` builds a fresh one per
    span. Treat an intent handed back by ``sampling_intent`` as shared either
    way, and never hold a reference expecting it to track later spans.

    Each field is documented on the field itself below.
    """

    threshold: int
    """The sampling threshold value. A lower threshold increases the likelihood of sampling.

    ``MIN_THRESHOLD`` samples every span. Any value that
    ``is_valid_threshold`` rejects, ``INVALID_THRESHOLD`` included, makes the
    composite sampler drop the span without comparing anything.
    """

    threshold_reliable: bool = field(default=True)
    """Indicates whether the threshold is reliable for Span-to-Metrics estimation.

    The decision is taken from the threshold either way. What changes is the
    outgoing trace state: when this is ``False`` the composite sampler leaves
    ``th`` out of the ``ot`` entry it writes, so no downstream consumer
    derives an adjusted count from a threshold that would not support one.
    The entry is written only when it serializes to a non-empty string, so a
    parent entry holding nothing but ``th`` is passed on unchanged.
    """

    attributes: Attributes = field(default=None)
    """Any attributes to be added to a sampled span.

    ``None`` adds nothing. The composite sampler copies the value into the
    ``SamplingResult`` without inspecting it.
    """

    update_trace_state: Callable[[TraceState], TraceState] = field(default=lambda ts: ts)
    """Any updates to be made to trace state.

    The default returns the trace state it is given, unchanged. The callable
    receives the trace state inherited from the parent and returns the
    replacement; the composite sampler then writes the ``ot`` entry on top of
    whatever comes back. It is called only when the parent trace state is
    present and non-empty, so a root span starting with no trace state never
    reaches it.
    """


class ComposableSampler(Protocol):
    """A sampler that can be composed to make a final sampling decision.

    Implementations are expected to be stateless and safe to call from several
    threads, since one sampler instance serves every span of a tracer
    provider. Wrap an implementation in ``composite_sampler`` to obtain an
    ordinary ``Sampler`` that a tracer provider accepts.
    """

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> SamplingIntent:
        """Returns information to make a sampling decision.

        The call happens before the span exists, so the arguments are the ones
        that would be passed to the span constructor. An implementation is not
        told the trace id and cannot compute the outcome itself.

        Args:
            parent_ctx: Context holding the parent span, or ``None`` to mean
                the current context. A parent span context that is not valid
                marks the span as a root.
            name: The name the span will be created with.
            span_kind: The kind the span will be created with, or ``None``
                when the caller supplied none.
            attributes: The attributes known at creation time, or ``None``.
                Attributes set after the span starts are not visible here.
            links: The links the span will be created with, or ``None``.
            trace_state: The trace state inherited from the parent, or
                ``None``. This is where the ``ot`` entry is read from.

        Returns:
            The intent carrying the threshold, whether that threshold is
            reliable, attributes to add, and a trace state update.
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def get_description(self) -> str:
        """Returns a description of the sampler.

        Returns:
            A string naming the sampler and the parameters it was built with.
            ``composite_sampler`` reports this verbatim as its own
            description, and a sampler that wraps others is expected to embed
            their descriptions in its own.
        """
        ...  # pylint: disable=unnecessary-ellipsis
