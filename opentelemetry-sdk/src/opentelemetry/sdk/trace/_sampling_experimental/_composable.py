# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Protocol

from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes


@dataclass(frozen=True)
class SamplingIntent:
    """Information to make a consistent sampling decision."""

    threshold: int
    """The sampling threshold value. A lower threshold increases the likelihood of sampling."""

    threshold_reliable: bool = field(default=True)
    """Indicates whether the threshold is reliable for Span-to-Metrics estimation."""

    attributes: Attributes = field(default=None)
    """Any attributes to be added to a sampled span."""

    update_trace_state: Callable[[TraceState], TraceState] = field(default=lambda ts: ts)
    """Any updates to be made to trace state."""


class ComposableSampler(Protocol):
    """A sampler that can be composed to make a final sampling decision."""

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
        *,
        span_type: str | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
        resource: Resource | None = None,
        **kwargs: Any,
    ) -> SamplingIntent:
        """Returns information to make a sampling decision.

        `span_type`, `instrumentation_scope`, `resource` and any further
        keyword-only inputs are additive: samplers written against the older
        signature keep working, see :func:`delegate_sampling_intent`.
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def get_description(self) -> str:
        """Returns a description of the sampler."""
        ...  # pylint: disable=unnecessary-ellipsis


def delegate_sampling_intent(
    sampler: ComposableSampler,
    parent_ctx: Context | None,
    name: str,
    span_kind: SpanKind | None,
    attributes: Attributes,
    links: Sequence[Link] | None,
    trace_state: TraceState | None,
    *,
    span_type: str | None = None,
    instrumentation_scope: InstrumentationScope | None = None,
    resource: Resource | None = None,
) -> SamplingIntent:
    """Calls `sampling_intent` on a delegate, dropping the keyword-only inputs
    it was not written to accept.

    `ComposableSampler` is a structural protocol, so a third-party sampler does
    not inherit a default implementation the way a `Sampler` subclass does.
    Passing the new inputs unconditionally would raise `TypeError` on every
    sampler written against the older signature.
    """
    if _accepts_keyword_inputs(sampler.sampling_intent):
        return sampler.sampling_intent(
            parent_ctx,
            name,
            span_kind,
            attributes,
            links,
            trace_state,
            span_type=span_type,
            instrumentation_scope=instrumentation_scope,
            resource=resource,
        )
    return sampler.sampling_intent(parent_ctx, name, span_kind, attributes, links, trace_state)


_KEYWORD_INPUTS = frozenset({"span_type", "instrumentation_scope", "resource"})


@cache
def _accepts_keyword_inputs(method: Callable[..., Any]) -> bool:
    try:
        parameters = inspect.signature(method).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name in _KEYWORD_INPUTS or parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters
    )
