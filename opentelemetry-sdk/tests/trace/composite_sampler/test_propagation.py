# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace._sampling_experimental import (
    ComposableSampler,
    SamplingIntent,
    composable_always_on,
    composable_parent_threshold,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._util import INVALID_THRESHOLD, MIN_THRESHOLD
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, Decision, ParentBased, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState, set_span_in_context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.util.types import Attributes


@pytest.mark.parametrize("parent_based", [False, True])
@pytest.mark.parametrize(
    "incoming,sampled,outgoing",
    [
        ("ot=th:8", False, None),
        ("vendora=alpha,ot=th:8", False, "vendora=alpha"),
        (
            "vendora=alpha,ot=th:8;rv:00000000000000",
            False,
            "ot=rv:00000000000000,vendora=alpha",
        ),
        ("vendora=alpha,ot=th:8;x:1", False, "ot=x:1,vendora=alpha"),
        (
            "vendora=alpha,ot=th:8;rv:ffffffffffffff",
            True,
            "ot=th:8;rv:ffffffffffffff,vendora=alpha",
        ),
    ],
)
def test_parent_threshold_propagation(incoming: str, sampled: bool, outgoing: str | None, parent_based: bool) -> None:
    propagator = TraceContextTextMapPropagator()
    parent = propagator.extract(
        {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            "tracestate": incoming,
        }
    )
    sampler = composite_sampler(composable_parent_threshold(composable_always_on()))
    if parent_based:
        sampler = ParentBased(root=ALWAYS_ON, remote_parent_sampled=sampler)
    provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
    try:
        with provider.get_tracer(__name__).start_span("child", context=parent) as span:
            assert span.get_span_context().trace_flags.sampled is sampled
            carrier: dict[str, str] = {}
            propagator.inject(carrier, context=set_span_in_context(span))
            assert carrier.get("tracestate") == outgoing
    finally:
        provider.shutdown()


@pytest.mark.parametrize("trace_state", [TraceState(), TraceState([("explicit", "value")])])
def test_explicit_tracestate_takes_precedence(trace_state: TraceState) -> None:
    parent = TraceContextTextMapPropagator().extract(
        {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            "tracestate": "parent=value",
        }
    )
    result = composite_sampler(composable_always_on()).should_sample(parent, 1, "child", trace_state=trace_state)
    assert result.trace_state is not None
    assert dict(result.trace_state.items()) == {**dict(trace_state.items()), "ot": "th:0"}


class _TaggingSampler(ComposableSampler):
    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> SamplingIntent:
        return SamplingIntent(
            threshold=MIN_THRESHOLD,
            update_trace_state=lambda ts: ts.add("vendorb", "beta"),
        )

    def get_description(self) -> str:
        return "Tagging"


@pytest.mark.parametrize("trace_state", [None, TraceState(), TraceState([("other", "1")])])
def test_sampling_intent_updates_tracestate(trace_state: TraceState | None) -> None:
    result = composite_sampler(_TaggingSampler()).should_sample(Context(), 1, "root", trace_state=trace_state)
    assert result.trace_state is not None
    assert dict(result.trace_state.items()) == {
        **dict((trace_state or TraceState()).items()),
        "vendorb": "beta",
        "ot": "th:0",
    }


def test_root_span_applies_tracestate_update() -> None:
    provider = TracerProvider(sampler=composite_sampler(_TaggingSampler()), shutdown_on_exit=False)
    try:
        with provider.get_tracer(__name__).start_span("root", context=Context()) as span:
            assert dict(span.get_span_context().trace_state.items()) == {"vendorb": "beta", "ot": "th:0"}
    finally:
        provider.shutdown()


@dataclass
class _OtelUpdatingSampler(ComposableSampler):
    threshold: int
    ot_value: str | None

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> SamplingIntent:
        return SamplingIntent(
            threshold=self.threshold,
            update_trace_state=lambda ts: (
                ts.update("ot", self.ot_value) if self.ot_value is not None else ts.delete("ot")
            ),
        )

    def get_description(self) -> str:
        return "OtelUpdating"


@pytest.mark.parametrize(
    "threshold,incoming,updated,outgoing",
    [
        (INVALID_THRESHOLD, "th:8", "x:1", "x:1"),
        (MIN_THRESHOLD, "th:8", "x:1", "th:0;x:1"),
        (
            INVALID_THRESHOLD,
            "th:8;rv:0123456789abcd;old:1",
            "th:0;rv:ffffffffffffff;x:1",
            "rv:0123456789abcd;x:1",
        ),
        (
            MIN_THRESHOLD,
            "th:8;rv:0123456789abcd;old:1",
            "th:8;rv:ffffffffffffff;x:1",
            "th:0;rv:0123456789abcd;x:1",
        ),
        (INVALID_THRESHOLD, "th:8;old:1", None, None),
        (INVALID_THRESHOLD, "th:8;rv:0123456789abcd;old:1", None, "rv:0123456789abcd"),
    ],
)
def test_callback_updates_ot_data(threshold: int, incoming: str, updated: str | None, outgoing: str | None) -> None:
    result = composite_sampler(_OtelUpdatingSampler(threshold, updated)).should_sample(
        Context(), 1, "span", trace_state=TraceState([("ot", incoming), ("vendor", "value")])
    )
    assert result.decision is (Decision.DROP if threshold == INVALID_THRESHOLD else Decision.RECORD_AND_SAMPLE)
    assert result.trace_state is not None
    expected = {"vendor": "value"}
    if outgoing is not None:
        expected["ot"] = outgoing
    assert dict(result.trace_state.items()) == expected


class _SixArgumentSampler(Sampler):
    # Deliberately omit the optional parameter to model existing custom samplers.
    def should_sample(  # pylint: disable=arguments-differ
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
    ) -> SamplingResult:
        return SamplingResult(Decision.RECORD_AND_SAMPLE)

    def get_description(self) -> str:
        return "SixArgumentSampler"


@pytest.mark.parametrize("parent_based", [False, True])
@pytest.mark.parametrize("remote_parent", [False, True])
def test_six_argument_sampler_compatibility(parent_based: bool, remote_parent: bool) -> None:
    sampler: Sampler = _SixArgumentSampler()
    if parent_based:
        sampler = ParentBased(root=sampler, remote_parent_sampled=sampler)
    parent = Context()
    if remote_parent:
        parent = TraceContextTextMapPropagator().extract(
            {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
        )
    provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
    try:
        with provider.get_tracer(__name__).start_span("span", context=parent) as span:
            assert span.is_recording()
    finally:
        provider.shutdown()
