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
                0x000000000000000000000000DEADBEEF,
                0x00000000DEADBEF0,
                trace_options=TO_DEFAULT,
            ),
            0x000000000000000000000000DEADBEF1,
            0x00000000DEADBEF2,
            "unrecorded parent, sampling on",
        )
        self.assertTrue(no_record_always_on.sampled)
        self.assertEqual(no_record_always_on.attributes, {})

        recorded_always_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF3,
                0x00000000DEADBEF4,
                trace_options=TO_RECORDED,
            ),
            0x000000000000000000000000DEADBEF5,
            0x00000000DEADBEF6,
            "recorded parent, sampling on",
        )
        self.assertTrue(recorded_always_on.sampled)
        self.assertEqual(recorded_always_on.attributes, {})

    def test_always_off(self):
        no_record_always_off = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=TO_DEFAULT,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "unrecorded parent, sampling off",
        )
        self.assertFalse(no_record_always_off.sampled)
        self.assertEqual(no_record_always_off.attributes, {})

        recorded_always_on = sampling.ALWAYS_OFF.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=TO_RECORDED,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "recorded parent, sampling off",
        )
        self.assertFalse(recorded_always_on.sampled)
        self.assertEqual(recorded_always_on.attributes, {})

    def test_default_on(self):
        no_record_default_on = sampling.DEFAULT_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEEF,
                0x00000000DEADBEF0,
                trace_options=TO_DEFAULT,
            ),
            0x000000000000000000000000DEADBEF1,
            0x00000000DEADBEF2,
            "unrecorded parent, sampling on",
        )
        self.assertFalse(no_record_default_on.sampled)
        self.assertEqual(no_record_default_on.attributes, {})

        recorded_default_on = sampling.DEFAULT_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF3,
                0x00000000DEADBEF4,
                trace_options=TO_RECORDED,
            ),
            0x000000000000000000000000DEADBEF5,
            0x00000000DEADBEF6,
            "recorded parent, sampling on",
        )
        self.assertTrue(recorded_default_on.sampled)
        self.assertEqual(recorded_default_on.attributes, {})

    def test_default_off(self):
        no_record_default_off = sampling.DEFAULT_OFF.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=TO_DEFAULT,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "unrecorded parent, sampling off",
        )
        self.assertFalse(no_record_default_off.sampled)
        self.assertEqual(no_record_default_off.attributes, {})

        recorded_default_off = sampling.DEFAULT_OFF.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=TO_RECORDED,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "recorded parent, sampling off",
        )
        self.assertTrue(recorded_default_off.sampled)
        self.assertEqual(recorded_default_off.attributes, {})
