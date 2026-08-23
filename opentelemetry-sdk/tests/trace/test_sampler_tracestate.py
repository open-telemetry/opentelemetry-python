# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Samplers must actually receive the parent's tracestate.

`Sampler.should_sample` declares a `trace_state` parameter and the consistent
probability sampling design in `_sampling_experimental` reads the parent
threshold out of it, so dropping it on the way in makes that machinery inert
and lets the composite sampler discard vendor tracestate entries.
"""

import unittest

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace._sampling_experimental import (
    ComposableSampler,
    SamplingIntent,
    composable_always_on,
    composable_parent_threshold,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._util import MIN_THRESHOLD
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,
    Decision,
    ParentBased,
    Sampler,
    SamplingResult,
)
from opentelemetry.trace import set_span_in_context
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

_CARRIER = {
    "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
    "tracestate": "vendora=alpha,ot=th:8",
}


class _SpySampler(Sampler):
    """Records the trace_state it was handed."""

    def __init__(self):
        self.seen = []

    def should_sample(
        self,
        parent_context,
        trace_id,
        name,
        kind=None,
        attributes=None,
        links=None,
        trace_state=None,
    ):
        self.seen.append(trace_state)
        return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes, trace_state)

    def get_description(self):
        return "Spy"


def _remote_context():
    return TraceContextTextMapPropagator().extract(dict(_CARRIER))


class TestSamplerReceivesTraceState(unittest.TestCase):
    def _run(self, sampler):
        provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
        provider.get_tracer(__name__).start_span("child", context=_remote_context())
        provider.shutdown()

    def test_sampler_receives_parent_tracestate(self):
        spy = _SpySampler()
        self._run(spy)
        self.assertIsNotNone(spy.seen[0])
        self.assertEqual(spy.seen[0].get("vendora"), "alpha")
        self.assertEqual(spy.seen[0].get("ot"), "th:8")

    def test_parent_based_forwards_tracestate_to_its_delegate(self):
        spy = _SpySampler()
        self._run(ParentBased(root=ALWAYS_ON, remote_parent_sampled=spy))
        self.assertIsNotNone(spy.seen[0])
        self.assertEqual(spy.seen[0].get("vendora"), "alpha")

    def test_root_span_receives_no_tracestate(self):
        """A root span has no parent, so None is correct here."""
        spy = _SpySampler()
        provider = TracerProvider(sampler=spy, shutdown_on_exit=False)
        provider.get_tracer(__name__).start_span("root")
        provider.shutdown()
        self.assertIsNone(spy.seen[0])


class TestCompositeSamplerPreservesTraceState(unittest.TestCase):
    def _outgoing_tracestate(self, sampler):
        provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
        span = provider.get_tracer(__name__).start_span("child", context=_remote_context())
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier, context=set_span_in_context(span))
        provider.shutdown()
        return carrier.get("tracestate")

    def test_vendor_entries_survive_the_composite_sampler(self):
        outgoing = self._outgoing_tracestate(
            composite_sampler(composable_parent_threshold(composable_always_on()))
        )
        self.assertIsNotNone(outgoing)
        self.assertIn("vendora=alpha", outgoing)

    def test_default_sampler_still_preserves_tracestate(self):
        """Control: the default sampler already got this right."""
        outgoing = self._outgoing_tracestate(None)
        self.assertIn("vendora=alpha", outgoing)


class TestSamplingIntentTraceStateUpdate(unittest.TestCase):
    """`SamplingIntent.update_trace_state` must run for root spans too."""

    class _TaggingSampler(ComposableSampler):
        def sampling_intent(self, parent_ctx, name, span_kind, attributes, links, trace_state):
            return SamplingIntent(
                threshold=MIN_THRESHOLD,
                update_trace_state=lambda ts: ts.add("vendorb", "beta"),
            )

        def get_description(self):
            return "Tagging"

    def setUp(self):
        self.sampler = composite_sampler(self._TaggingSampler())
        self.trace_id = 0x0AF7651916CD43DD8448EB211C80319C

    def test_applied_when_incoming_tracestate_is_absent(self):
        result = self.sampler.should_sample(None, self.trace_id, "op", trace_state=None)
        self.assertIsNotNone(result.trace_state)
        self.assertEqual(result.trace_state.get("vendorb"), "beta")

    def test_applied_when_incoming_tracestate_is_present(self):
        from opentelemetry.trace import TraceState

        result = self.sampler.should_sample(
            None, self.trace_id, "op", trace_state=TraceState([("other", "1")])
        )
        self.assertEqual(result.trace_state.get("vendorb"), "beta")
        self.assertEqual(result.trace_state.get("other"), "1")
