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

import contextlib
import sys
import typing
import unittest

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.sdk.trace import sampling

TO_DEFAULT = trace.TraceFlags(trace.TraceFlags.DEFAULT)
TO_SAMPLED = trace.TraceFlags(trace.TraceFlags.SAMPLED)


class TestDecision(unittest.TestCase):
    def test_is_recording(self):
        self.assertTrue(
            sampling.Decision.is_recording(sampling.Decision.RECORD_ONLY)
        )
        self.assertTrue(
            sampling.Decision.is_recording(sampling.Decision.RECORD_AND_SAMPLE)
        )
        self.assertFalse(
            sampling.Decision.is_recording(sampling.Decision.DROP)
        )

    def test_is_sampled(self):
        self.assertFalse(
            sampling.Decision.is_sampled(sampling.Decision.RECORD_ONLY)
        )
        self.assertTrue(
            sampling.Decision.is_sampled(sampling.Decision.RECORD_AND_SAMPLE)
        )
        self.assertFalse(sampling.Decision.is_sampled(sampling.Decision.DROP))


class TestSamplingResult(unittest.TestCase):
    def test_ctr(self):
        attributes = {"asd": "test"}
        trace_state = {}
        # pylint: disable=E1137
        trace_state["test"] = "123"
        result = sampling.SamplingResult(
            sampling.Decision.RECORD_ONLY, attributes, trace_state
        )
        self.assertIs(result.decision, sampling.Decision.RECORD_ONLY)
        with self.assertRaises(TypeError):
            result.attributes["test"] = "mess-this-up"
        self.assertTrue(len(result.attributes), 1)
        self.assertEqual(result.attributes["asd"], "test")
        self.assertEqual(result.trace_state["test"], "123")


class TestSampler(unittest.TestCase):
    def _create_parent(
        self, trace_flags: trace.TraceFlags, is_remote=False, trace_state=None
    ) -> typing.Optional[context_api.Context]:
        if trace_flags is None:
            return None
        return trace.set_span_in_context(
            self._create_parent_span(trace_flags, is_remote, trace_state)
        )

    @staticmethod
    def _create_parent_span(
        trace_flags: trace.TraceFlags, is_remote=False, trace_state=None
    ) -> trace.NonRecordingSpan:
        return trace.NonRecordingSpan(
            trace.SpanContext(
                0xDEADBEEF,
                0xDEADBEF0,
                is_remote=is_remote,
                trace_flags=trace_flags,
                trace_state=trace_state,
            )
        )

    def test_always_on(self):
        trace_state = trace.TraceState([("key", "value")])
        test_data = (TO_DEFAULT, TO_SAMPLED, None)

        for trace_flags in test_data:
            with self.subTest(trace_flags=trace_flags):
                context = self._create_parent(trace_flags, False, trace_state)
                sample_result = sampling.ALWAYS_ON.should_sample(
                    context,
                    0xDEADBEF1,
                    "sampling on",
                    trace.SpanKind.INTERNAL,
                    attributes={"sampled.expect": "true"},
                )

                self.assertTrue(sample_result.decision.is_sampled())
                self.assertEqual(
                    sample_result.attributes, {"sampled.expect": "true"}
                )
                if context is not None:
                    self.assertEqual(sample_result.trace_state, trace_state)
                else:
                    self.assertIsNone(sample_result.trace_state)

    def test_always_off(self):
        trace_state = trace.TraceState([("key", "value")])
        test_data = (TO_DEFAULT, TO_SAMPLED, None)
        for trace_flags in test_data:
            with self.subTest(trace_flags=trace_flags):
                context = self._create_parent(trace_flags, False, trace_state)
                sample_result = sampling.ALWAYS_OFF.should_sample(
                    context,
                    0xDEADBEF1,
                    "sampling off",
                    trace.SpanKind.INTERNAL,
                    attributes={"sampled.expect": "false"},
                )
                self.assertFalse(sample_result.decision.is_sampled())
                self.assertEqual(sample_result.attributes, {})
                if context is not None:
                    self.assertEqual(sample_result.trace_state, trace_state)
                else:
                    self.assertIsNone(sample_result.trace_state)

    def test_default_on(self):
        trace_state = trace.TraceState([("key", "value")])
        context = self._create_parent(TO_DEFAULT, False, trace_state)
        sample_result = sampling.DEFAULT_ON.should_sample(
            context,
            0xDEADBEF1,
            "unsampled parent, sampling on",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "false"},
        )
        self.assertFalse(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {})
        self.assertEqual(sample_result.trace_state, trace_state)

        context = self._create_parent(TO_SAMPLED, False, trace_state)
        sample_result = sampling.DEFAULT_ON.should_sample(
            context,
            0xDEADBEF1,
            "sampled parent, sampling on",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "true"},
        )
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {"sampled.expect": "true"})
        self.assertEqual(sample_result.trace_state, trace_state)

        sample_result = sampling.DEFAULT_ON.should_sample(
            None,
            0xDEADBEF1,
            "no parent, sampling on",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "true"},
        )
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {"sampled.expect": "true"})
        self.assertIsNone(sample_result.trace_state)

    def test_default_off(self):
        trace_state = trace.TraceState([("key", "value")])
        context = self._create_parent(TO_DEFAULT, False, trace_state)
        sample_result = sampling.DEFAULT_OFF.should_sample(
            context,
            0xDEADBEF1,
            "unsampled parent, sampling off",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect", "false"},
        )
        self.assertFalse(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {})
        self.assertEqual(sample_result.trace_state, trace_state)

        context = self._create_parent(TO_SAMPLED, False, trace_state)
        sample_result = sampling.DEFAULT_OFF.should_sample(
            context,
            0xDEADBEF1,
            "sampled parent, sampling on",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "true"},
        )
        self.assertTrue(sample_result.decision.is_sampled())
        self.assertEqual(sample_result.attributes, {"sampled.expect": "true"})
        self.assertEqual(sample_result.trace_state, trace_state)

        default_off = sampling.DEFAULT_OFF.should_sample(
            None,
            0xDEADBEF1,
            "unsampled parent, sampling off",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "false"},
        )
        self.assertFalse(default_off.decision.is_sampled())
        self.assertEqual(default_off.attributes, {})
        self.assertIsNone(default_off.trace_state)

    def test_probability_sampler(self):
        sampler = sampling.TraceIdRatioBased(0.5)

        # Check that we sample based on the trace ID if the parent context is
        # null
        # trace_state should also be empty since it is based off of parent
        sampled_result = sampler.should_sample(
            None,
            0x7FFFFFFFFFFFFFFF,
            "sampled true",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "true"},
        )
        self.assertTrue(sampled_result.decision.is_sampled())
        self.assertEqual(sampled_result.attributes, {"sampled.expect": "true"})
        self.assertIsNone(sampled_result.trace_state)

        not_sampled_result = sampler.should_sample(
            None,
            0x8000000000000000,
            "sampled false",
            trace.SpanKind.INTERNAL,
            attributes={"sampled.expect": "false"},
        )
        self.assertFalse(not_sampled_result.decision.is_sampled())
        self.assertEqual(not_sampled_result.attributes, {})
        self.assertIsNone(sampled_result.trace_state)

    def test_probability_sampler_zero(self):
        default_off = sampling.TraceIdRatioBased(0.0)
        self.assertFalse(
            default_off.should_sample(
                None, 0x0, "span name"
            ).decision.is_sampled()
        )

    def test_probability_sampler_one(self):
        default_off = sampling.TraceIdRatioBased(1.0)
        self.assertTrue(
            default_off.should_sample(
                None, 0xFFFFFFFFFFFFFFFF, "span name"
            ).decision.is_sampled()
        )

    def test_probability_sampler_limits(self):

        # Sample one of every 2^64 (= 5e-20) traces. This is the lowest
        # possible meaningful sampling rate, only traces with trace ID 0x0
        # should get sampled.
        almost_always_off = sampling.TraceIdRatioBased(2**-64)
        self.assertTrue(
            almost_always_off.should_sample(
                None, 0x0, "span name"
            ).decision.is_sampled()
        )
        self.assertFalse(
            almost_always_off.should_sample(
                None, 0x1, "span name"
            ).decision.is_sampled()
        )
        self.assertEqual(
            sampling.TraceIdRatioBased.get_bound_for_rate(2**-64), 0x1
        )

        # Sample every trace with trace ID less than 0xffffffffffffffff. In
        # principle this is the highest possible sampling rate less than 1, but
        # we can't actually express this rate as a float!
        #
        # In practice, the highest possible sampling rate is:
        #
        #     1 - sys.float_info.epsilon

        almost_always_on = sampling.TraceIdRatioBased(1 - 2**-64)
        self.assertTrue(
            almost_always_on.should_sample(
                None, 0xFFFFFFFFFFFFFFFE, "span name"
            ).decision.is_sampled()
        )

        # These tests are logically consistent, but fail because of the float
        # precision issue above. Changing the sampler to check fewer bytes of
        # the trace ID will cause these to pass.

        # self.assertFalse(
        #     almost_always_on.should_sample(
        #         None,
        #         0xFFFFFFFFFFFFFFFF,
        #         "span name",
        #     ).decision.is_sampled()
        # )
        # self.assertEqual(
        #     sampling.TraceIdRatioBased.get_bound_for_rate(1 - 2 ** -64)),
        #     0xFFFFFFFFFFFFFFFF,
        # )

        # Check that a sampler with the highest effective sampling rate < 1
        # refuses to sample traces with trace ID 0xffffffffffffffff.
        almost_almost_always_on = sampling.TraceIdRatioBased(
            1 - sys.float_info.epsilon
        )
        self.assertFalse(
            almost_almost_always_on.should_sample(
                None, 0xFFFFFFFFFFFFFFFF, "span name"
            ).decision.is_sampled()
        )
        # Check that the highest effective sampling rate is actually lower than
        # the highest theoretical sampling rate. If this test fails the test
        # above is wrong.
        self.assertLess(
            almost_almost_always_on.bound,
            0xFFFFFFFFFFFFFFFF,
        )

    # pylint:disable=too-many-statements
    def exec_parent_based(self, parent_sampling_context):
        trace_state = trace.TraceState([("key", "value")])
        sampler = sampling.ParentBased(sampling.ALWAYS_ON)
        # Check that the sampling decision matches the parent context if given
        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_DEFAULT,
                trace_state=trace_state,
            )
        ) as context:
            # local, not sampled
            not_sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
            )
            self.assertFalse(not_sampled_result.decision.is_sampled())
            self.assertEqual(not_sampled_result.attributes, {})
            self.assertEqual(not_sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_DEFAULT,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(
                root=sampling.ALWAYS_OFF,
                local_parent_not_sampled=sampling.ALWAYS_ON,
            )
            # local, not sampled -> opposite sampler
            sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
            )
            self.assertTrue(sampled_result.decision.is_sampled())
            self.assertEqual(sampled_result.attributes, {"sampled": "false"})
            self.assertEqual(sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_SAMPLED,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(sampling.ALWAYS_OFF)
            # local, sampled
            sampled_result = sampler.should_sample(
                context,
                0x8000000000000000,
                "sampled parent, sampling off",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "true"},
                trace_state=trace_state,
            )
            self.assertTrue(sampled_result.decision.is_sampled())
            self.assertEqual(sampled_result.attributes, {"sampled": "true"})
            self.assertEqual(sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_SAMPLED,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(
                root=sampling.ALWAYS_ON,
                local_parent_sampled=sampling.ALWAYS_OFF,
            )
            # local, sampled -> opposite sampler
            not_sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
                trace_state=trace_state,
            )
            self.assertFalse(not_sampled_result.decision.is_sampled())
            self.assertEqual(not_sampled_result.attributes, {})
            self.assertEqual(not_sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_DEFAULT,
                is_remote=True,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(sampling.ALWAYS_ON)
            # remote, not sampled
            not_sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
                trace_state=trace_state,
            )
            self.assertFalse(not_sampled_result.decision.is_sampled())
            self.assertEqual(not_sampled_result.attributes, {})
            self.assertEqual(not_sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_DEFAULT,
                is_remote=True,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(
                root=sampling.ALWAYS_OFF,
                remote_parent_not_sampled=sampling.ALWAYS_ON,
            )
            # remote, not sampled -> opposite sampler
            sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
            )
            self.assertTrue(sampled_result.decision.is_sampled())
            self.assertEqual(sampled_result.attributes, {"sampled": "false"})
            self.assertEqual(sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_SAMPLED,
                is_remote=True,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(sampling.ALWAYS_OFF)
            # remote, sampled
            sampled_result = sampler.should_sample(
                context,
                0x8000000000000000,
                "sampled parent, sampling off",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "true"},
            )
            self.assertTrue(sampled_result.decision.is_sampled())
            self.assertEqual(sampled_result.attributes, {"sampled": "true"})
            self.assertEqual(sampled_result.trace_state, trace_state)

        with parent_sampling_context(
            self._create_parent_span(
                trace_flags=TO_SAMPLED,
                is_remote=True,
                trace_state=trace_state,
            )
        ) as context:
            sampler = sampling.ParentBased(
                root=sampling.ALWAYS_ON,
                remote_parent_sampled=sampling.ALWAYS_OFF,
            )
            # remote, sampled -> opposite sampler
            not_sampled_result = sampler.should_sample(
                context,
                0x7FFFFFFFFFFFFFFF,
                "unsampled parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
            )
            self.assertFalse(not_sampled_result.decision.is_sampled())
            self.assertEqual(not_sampled_result.attributes, {})
            self.assertEqual(not_sampled_result.trace_state, trace_state)

        # for root span follow decision of root sampler
        with parent_sampling_context(trace.INVALID_SPAN) as context:
            sampler = sampling.ParentBased(sampling.ALWAYS_OFF)
            not_sampled_result = sampler.should_sample(
                context,
                0x8000000000000000,
                "parent, sampling off",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "false"},
            )
            self.assertFalse(not_sampled_result.decision.is_sampled())
            self.assertEqual(not_sampled_result.attributes, {})
            self.assertIsNone(not_sampled_result.trace_state)

        with parent_sampling_context(trace.INVALID_SPAN) as context:
            sampler = sampling.ParentBased(sampling.ALWAYS_ON)
            sampled_result = sampler.should_sample(
                context,
                0x8000000000000000,
                "no parent, sampling on",
                trace.SpanKind.INTERNAL,
                attributes={"sampled": "true"},
                trace_state=trace_state,
            )
            self.assertTrue(sampled_result.decision.is_sampled())
            self.assertEqual(sampled_result.attributes, {"sampled": "true"})
            self.assertIsNone(sampled_result.trace_state)

    def test_parent_based_explicit_parent_context(self):
        @contextlib.contextmanager
        def explicit_parent_context(span: trace.Span):
            yield trace.set_span_in_context(span)

        self.exec_parent_based(explicit_parent_context)

    def test_parent_based_implicit_parent_context(self):
        @contextlib.contextmanager
        def implicit_parent_context(span: trace.Span):
            token = context_api.attach(trace.set_span_in_context(span))
            yield None
            context_api.detach(token)

        self.exec_parent_based(implicit_parent_context)
