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

import sys
import unittest

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
        result = sampling.SamplingResult(
            sampling.Decision.RECORD_ONLY, attributes
        )
        self.assertIs(result.decision, sampling.Decision.RECORD_ONLY)
        with self.assertRaises(TypeError):
            result.attributes["test"] = "mess-this-up"
        self.assertTrue(len(result.attributes), 1)
        self.assertEqual(result.attributes["asd"], "test")


class TestSampler(unittest.TestCase):
    def test_always_on(self):
        no_record_always_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, is_remote=False, trace_flags=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            {"unsampled parent": "sampling on"},
        )
        self.assertTrue(no_record_always_on.decision.is_sampled())
        self.assertEqual(
            no_record_always_on.attributes, {"unsampled parent": "sampling on"}
        )

        sampled_always_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, is_remote=False, trace_flags=TO_SAMPLED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            {"sampled parent": "sampling on"},
        )
        self.assertTrue(no_record_always_on.decision.is_sampled())
        self.assertEqual(
            sampled_always_on.attributes, {"sampled parent": "sampling on"}
        )

    def test_always_off(self):
        no_record_always_off = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, is_remote=False, trace_flags=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "unsampled parent, sampling off",
        )
        self.assertFalse(no_record_always_off.decision.is_sampled())
        self.assertEqual(no_record_always_off.attributes, {})

        sampled_always_on = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, is_remote=False, trace_flags=TO_SAMPLED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "sampled parent, sampling off",
        )
        self.assertFalse(sampled_always_on.decision.is_sampled())
        self.assertEqual(sampled_always_on.attributes, {})

    def test_default_on(self):
        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEEF,
                    0xDEADBEF0,
                    is_remote=False,
                    trace_flags=TO_DEFAULT,
                )
            )
        )
        no_record_default_on = sampling.DEFAULT_ON.should_sample(
            context, 0xDEADBEF1, 0xDEADBEF2, "unsampled parent, sampling on",
        )
        self.assertFalse(no_record_default_on.decision.is_sampled())
        self.assertEqual(no_record_default_on.attributes, {})

        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEEF,
                    0xDEADBEF0,
                    is_remote=False,
                    trace_flags=TO_SAMPLED,
                )
            )
        )
        sampled_default_on = sampling.DEFAULT_ON.should_sample(
            context, 0xDEADBEF1, 0xDEADBEF2, {"sampled parent": "sampling on"},
        )
        self.assertTrue(sampled_default_on.decision.is_sampled())
        self.assertEqual(
            sampled_default_on.attributes, {"sampled parent": "sampling on"}
        )

        default_on = sampling.DEFAULT_ON.should_sample(
            None, 0xDEADBEF1, 0xDEADBEF2, {"sampled parent": "sampling on"},
        )
        self.assertTrue(default_on.decision.is_sampled())
        self.assertEqual(
            default_on.attributes, {"sampled parent": "sampling on"}
        )

    def test_default_off(self):
        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEEF,
                    0xDEADBEF0,
                    is_remote=False,
                    trace_flags=TO_DEFAULT,
                )
            )
        )
        no_record_default_off = sampling.DEFAULT_OFF.should_sample(
            context, 0xDEADBEF1, 0xDEADBEF2, "unsampled parent, sampling off",
        )
        self.assertFalse(no_record_default_off.decision.is_sampled())
        self.assertEqual(no_record_default_off.attributes, {})

        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEEF,
                    0xDEADBEF0,
                    is_remote=False,
                    trace_flags=TO_SAMPLED,
                )
            )
        )
        sampled_default_off = sampling.DEFAULT_OFF.should_sample(
            context, 0xDEADBEF1, 0xDEADBEF2, {"sampled parent": "sampling on"},
        )
        self.assertTrue(sampled_default_off.decision.is_sampled())
        self.assertEqual(
            sampled_default_off.attributes, {"sampled parent": "sampling on"}
        )

        default_off = sampling.DEFAULT_OFF.should_sample(
            None, 0xDEADBEF1, 0xDEADBEF2, "unsampled parent, sampling off",
        )
        self.assertFalse(default_off.decision.is_sampled())
        self.assertEqual(default_off.attributes, {})

    def test_probability_sampler(self):
        sampler = sampling.TraceIdRatioBased(0.5)

        # Check that we sample based on the trace ID if the parent context is
        # null
        self.assertTrue(
            sampler.should_sample(
                None, 0x7FFFFFFFFFFFFFFF, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )
        self.assertFalse(
            sampler.should_sample(
                None, 0x8000000000000000, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )

    def test_probability_sampler_zero(self):
        default_off = sampling.TraceIdRatioBased(0.0)
        self.assertFalse(
            default_off.should_sample(
                None, 0x0, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )

    def test_probability_sampler_one(self):
        default_off = sampling.TraceIdRatioBased(1.0)
        self.assertTrue(
            default_off.should_sample(
                None, 0xFFFFFFFFFFFFFFFF, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )

    def test_probability_sampler_limits(self):

        # Sample one of every 2^64 (= 5e-20) traces. This is the lowest
        # possible meaningful sampling rate, only traces with trace ID 0x0
        # should get sampled.
        almost_always_off = sampling.TraceIdRatioBased(2 ** -64)
        self.assertTrue(
            almost_always_off.should_sample(
                None, 0x0, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )
        self.assertFalse(
            almost_always_off.should_sample(
                None, 0x1, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )
        self.assertEqual(
            sampling.TraceIdRatioBased.get_bound_for_rate(2 ** -64), 0x1
        )

        # Sample every trace with trace ID less than 0xffffffffffffffff. In
        # principle this is the highest possible sampling rate less than 1, but
        # we can't actually express this rate as a float!
        #
        # In practice, the highest possible sampling rate is:
        #
        #     1 - sys.float_info.epsilon

        almost_always_on = sampling.TraceIdRatioBased(1 - 2 ** -64)
        self.assertTrue(
            almost_always_on.should_sample(
                None, 0xFFFFFFFFFFFFFFFE, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )

        # These tests are logically consistent, but fail because of the float
        # precision issue above. Changing the sampler to check fewer bytes of
        # the trace ID will cause these to pass.

        # self.assertFalse(
        #     almost_always_on.should_sample(
        #         None,
        #         0xFFFFFFFFFFFFFFFF,
        #         0xDEADBEEF,
        #         "span name",
        #     ).sampled
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
                None, 0xFFFFFFFFFFFFFFFF, 0xDEADBEEF, "span name"
            ).decision.is_sampled()
        )
        # Check that the higest effective sampling rate is actually lower than
        # the highest theoretical sampling rate. If this test fails the test
        # above is wrong.
        self.assertLess(
            almost_almost_always_on.bound, 0xFFFFFFFFFFFFFFFF,
        )

    def test_parent_based(self):
        sampler = sampling.ParentBased(sampling.ALWAYS_ON)
        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEF0,
                    0xDEADBEF1,
                    is_remote=False,
                    trace_flags=TO_DEFAULT,
                )
            )
        )
        # Check that the sampling decision matches the parent context if given
        self.assertFalse(
            sampler.should_sample(
                context, 0x7FFFFFFFFFFFFFFF, 0xDEADBEEF, "span name",
            ).decision.is_sampled()
        )

        context = trace.set_span_in_context(
            trace.DefaultSpan(
                trace.SpanContext(
                    0xDEADBEF0,
                    0xDEADBEF1,
                    is_remote=False,
                    trace_flags=TO_SAMPLED,
                )
            )
        )
        sampler2 = sampling.ParentBased(sampling.ALWAYS_OFF)
        self.assertTrue(
            sampler2.should_sample(
                context, 0x8000000000000000, 0xDEADBEEF, "span name",
            ).decision.is_sampled()
        )

        # root span always sampled for parentbased
        context = trace.set_span_in_context(trace.INVALID_SPAN)
        sampler3 = sampling.ParentBased(sampling.ALWAYS_OFF)
        self.assertTrue(
            sampler3.should_sample(
                context, 0x8000000000000000, 0xDEADBEEF, "span name",
            ).decision.is_sampled()
        )
