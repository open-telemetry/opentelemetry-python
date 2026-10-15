# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.test.samplertestutil import CapturingSampler
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    SpanKind,
    TraceFlags,
    TraceState,
    set_span_in_context,
)


class TestCapturingSampler(TestCase):
    def test_nothing_captured_before_sampling(self):
        sampler = CapturingSampler()

        self.assertIsNone(sampler.name)
        self.assertIsNone(sampler.kind)
        self.assertEqual(sampler.attributes, {})
        self.assertEqual(sampler.get_description(), "CapturingSampler")

    def test_captures_sampling_arguments(self):
        sampler = CapturingSampler()
        attributes = {"http.request.header.custom_test_header_1": ["value"]}

        result = sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, attributes)

        self.assertEqual(result.decision, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(dict(result.attributes), attributes)
        self.assertIsNone(result.trace_state)
        self.assertEqual(sampler.name, "request")
        self.assertEqual(sampler.kind, SpanKind.SERVER)
        self.assertEqual(sampler.attributes, attributes)

    def test_captured_attributes_are_a_snapshot(self):
        sampler = CapturingSampler()
        attributes = {"first": "value"}

        sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, attributes)
        attributes["second"] = "value"

        self.assertEqual(sampler.attributes, {"first": "value"})

    def test_captures_last_call(self):
        sampler = CapturingSampler()

        sampler.should_sample(None, 0x1, "first", SpanKind.SERVER, {"first": 1})
        sampler.should_sample(None, 0x1, "second", SpanKind.INTERNAL)

        self.assertEqual(sampler.name, "second")
        self.assertEqual(sampler.kind, SpanKind.INTERNAL)
        self.assertEqual(sampler.attributes, {})

    def test_required_attributes(self):
        sampler = CapturingSampler(required_attributes={"tenant": ["sample"]})

        for attributes in ({"tenant": ["drop"]}, {"other": ["sample"]}, None):
            with self.subTest(attributes=attributes):
                result = sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, attributes)

                self.assertEqual(result.decision, Decision.DROP)
                self.assertEqual(dict(result.attributes), {})
                self.assertEqual(sampler.attributes, attributes or {})

        attributes = {"tenant": ["sample"], "other": ["value"]}
        result = sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, attributes)

        self.assertEqual(result.decision, Decision.RECORD_AND_SAMPLE)
        self.assertEqual(dict(result.attributes), attributes)
        self.assertEqual(sampler.attributes, attributes)

    def test_required_attribute_expected_to_be_none_must_be_present(self):
        sampler = CapturingSampler(required_attributes={"tenant": None})

        result = sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, {"other": "value"})

        self.assertEqual(result.decision, Decision.DROP)
        self.assertEqual(dict(result.attributes), {})

        result = sampler.should_sample(None, 0x1, "request", SpanKind.SERVER, {"tenant": None})

        self.assertEqual(result.decision, Decision.RECORD_AND_SAMPLE)

    def test_keeps_parent_trace_state(self):
        sampler = CapturingSampler()
        trace_state = TraceState([("vendor", "value")])
        parent = NonRecordingSpan(
            SpanContext(
                trace_id=0x1,
                span_id=0x2,
                is_remote=True,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
                trace_state=trace_state,
            )
        )

        result = sampler.should_sample(set_span_in_context(parent), 0x1, "request")

        self.assertEqual(result.trace_state, trace_state)

    def test_tracer_provider(self):
        sampler = CapturingSampler(required_attributes={"tenant": "sampled"})
        tracer_provider, exporter = TestBase.create_tracer_provider(sampler=sampler)
        self.addCleanup(tracer_provider.shutdown)
        tracer = tracer_provider.get_tracer(__name__)

        with tracer.start_as_current_span("kept", kind=SpanKind.SERVER, attributes={"tenant": "sampled"}) as span:
            self.assertTrue(span.is_recording())
            self.assertEqual(sampler.name, "kept")
            self.assertEqual(sampler.kind, SpanKind.SERVER)
            self.assertEqual(sampler.attributes, {"tenant": "sampled"})

        with tracer.start_as_current_span("dropped", attributes={"tenant": "other"}) as span:
            self.assertFalse(span.is_recording())
            self.assertEqual(sampler.name, "dropped")
            self.assertEqual(sampler.kind, SpanKind.INTERNAL)
            self.assertEqual(sampler.attributes, {"tenant": "other"})

        spans = exporter.get_finished_spans()
        self.assertEqual([span.name for span in spans], ["kept"])
        self.assertEqual(spans[0].kind, SpanKind.SERVER)
        self.assertEqual(dict(spans[0].attributes), {"tenant": "sampled"})
