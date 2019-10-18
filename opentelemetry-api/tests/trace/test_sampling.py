# Copyright 2019, OpenTelemetry Authors
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

import unittest

from opentelemetry import trace
from opentelemetry.trace import sampling

TO_DEFAULT = trace.TraceOptions(trace.TraceOptions.DEFAULT)
TO_RECORDED = trace.TraceOptions(trace.TraceOptions.RECORDED)


class TestSampler(unittest.TestCase):
    def test_always_on(self):
        no_record_always_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "unrecorded parent, sampling on",
        )
        self.assertTrue(no_record_always_on.sampled)
        self.assertEqual(no_record_always_on.attributes, {})

        recorded_always_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_RECORDED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "recorded parent, sampling on",
        )
        self.assertTrue(recorded_always_on.sampled)
        self.assertEqual(recorded_always_on.attributes, {})

    def test_always_off(self):
        no_record_always_off = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "unrecorded parent, sampling off",
        )
        self.assertFalse(no_record_always_off.sampled)
        self.assertEqual(no_record_always_off.attributes, {})

        recorded_always_on = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_RECORDED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "recorded parent, sampling off",
        )
        self.assertFalse(recorded_always_on.sampled)
        self.assertEqual(recorded_always_on.attributes, {})

    def test_default_on(self):
        no_record_default_on = sampling.DEFAULT_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "unrecorded parent, sampling on",
        )
        self.assertFalse(no_record_default_on.sampled)
        self.assertEqual(no_record_default_on.attributes, {})

        recorded_default_on = sampling.DEFAULT_ON.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_RECORDED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "recorded parent, sampling on",
        )
        self.assertTrue(recorded_default_on.sampled)
        self.assertEqual(recorded_default_on.attributes, {})

    def test_default_off(self):
        no_record_default_off = sampling.DEFAULT_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_DEFAULT
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "unrecorded parent, sampling off",
        )
        self.assertFalse(no_record_default_off.sampled)
        self.assertEqual(no_record_default_off.attributes, {})

        recorded_default_off = sampling.DEFAULT_OFF.should_sample(
            trace.SpanContext(
                0xDEADBEEF, 0xDEADBEF0, trace_options=TO_RECORDED
            ),
            0xDEADBEF1,
            0xDEADBEF2,
            "recorded parent, sampling off",
        )
        self.assertTrue(recorded_default_off.sampled)
        self.assertEqual(recorded_default_off.attributes, {})

    def test_probability_sampler(self):
        sampler = sampling.ProbabilitySampler(0.5)

        # Check that we sample based on the trace ID if the parent context is
        # null
        self.assertTrue(
            sampler.should_sample(
                None, 0x7FFFFFFFFFFFFFFF, 0xDEADBEEF, "span name"
            ).sampled
        )
        self.assertFalse(
            sampler.should_sample(
                None, 0x8000000000000000, 0xDEADBEEF, "span name"
            ).sampled
        )

        # Check that the sampling decision matches the parent context if given,
        # and that the sampler ignores the trace ID
        self.assertFalse(
            sampler.should_sample(
                trace.SpanContext(
                    0xDEADBEF0, 0xDEADBEF1, trace_options=TO_DEFAULT
                ),
                0x8000000000000000,
                0xDEADBEEF,
                "span name",
            ).sampled
        )
        self.assertTrue(
            sampler.should_sample(
                trace.SpanContext(
                    0xDEADBEF0, 0xDEADBEF1, trace_options=TO_RECORDED
                ),
                0x8000000000000001,
                0xDEADBEEF,
                "span name",
            ).sampled
        )

    def test_probability_sampler_zero(self):
        default_off = sampling.ProbabilitySampler(0.0)
        self.assertFalse(
            default_off.should_sample(
                None, 0x0, 0xDEADBEEF, "span name"
            ).sampled
        )

    def test_probability_sampler_one(self):
        default_off = sampling.ProbabilitySampler(1.0)
        self.assertTrue(
            default_off.should_sample(
                None, 0xFFFFFFFFFFFFFFFF, 0xDEADBEEF, "span name"
            ).sampled
        )

    def test_probability_sampler_limits(self):

        # Sample one of every 2^64 (= 5e-20) traces. This is the lowest
        # possible meaningful sampling rate, only traces with trace ID 0x0
        # should get sampled.
        almost_always_off = sampling.ProbabilitySampler(2 ** -64)
        self.assertTrue(
            almost_always_off.should_sample(
                None, 0x0, 0xDEADBEEF, "span name"
            ).sampled
        )
        self.assertFalse(
            almost_always_off.should_sample(
                None, 0x1, 0xDEADBEEF, "span name"
            ).sampled
        )
        self.assertEqual(
            sampling.ProbabilitySampler.get_bound_for_rate(2 ** -64), 0x1
        )

        # Sample every trace with (last 8 bytes of) trace ID less than
        # 0xffffffffffffffff. In principle this is the highest possible
        # sampling rate less than 1, but we can't actually express this rate as
        # a float!
        #
        # In practice, the highest possible sampling rate is:
        #
        #     round(sys.float_info.epsilon * 2 ** 64)

        almost_always_on = sampling.ProbabilitySampler(1 - 2 ** -64)
        self.assertTrue(
            almost_always_on.should_sample(
                None, 0xFFFFFFFFFFFFFFFE, 0xDEADBEEF, "span name"
            ).sampled
        )

        # These tests are logically consistent, but fail because of the float
        # precision issue above. Changing the sampler to check fewer bytes of
        # the trace ID will cause these to pass.

        # self.assertFalse(
        #     almost_always_on.should_sample(
        #         None,
        #         0xffffffffffffffff,
        #         0xdeadbeef,
        #         "span name",
        #     ).sampled
        # )
        # self.assertEqual(
        #     sampling.ProbabilitySampler.get_bound_for_rate(1 - 2 ** -64)),
        #     0xffffffffffffffff,
        # )
