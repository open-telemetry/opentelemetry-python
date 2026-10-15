# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
    """

    name: str | None
    kind: SpanKind | None
    attributes: dict[str, AttributeValue]

    def __init__(self, required_attributes: Attributes = None) -> None:
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
        return "CapturingSampler"
