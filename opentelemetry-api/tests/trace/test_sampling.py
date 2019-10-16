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


class TestSampler(unittest.TestCase):
    def test_always_on(self):
        unrecorded_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEEF,
                0x00000000DEADBEF0,
                trace_options=trace.TraceOptions.DEFAULT,
            ),
            0x000000000000000000000000DEADBEF1,
            0x00000000DEADBEF2,
            "unrecorded parent, sampling on",
        )
        self.assertTrue(unrecorded_on.sampled)
        self.assertEqual(unrecorded_on.attributes, {})

        recorded_on = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF3,
                0x00000000DEADBEF4,
                trace_options=trace.TraceOptions.DEFAULT,
            ),
            0x000000000000000000000000DEADBEF5,
            0x00000000DEADBEF6,
            "recorded parent, sampling on",
        )
        self.assertTrue(recorded_on.sampled)
        self.assertEqual(recorded_on.attributes, {})

    def test_always_off(self):
        unrecorded_off = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=trace.TraceOptions.DEFAULT,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "recorded parent, sampling off",
        )
        self.assertTrue(unrecorded_off.sampled)
        self.assertEqual(unrecorded_off.attributes, {})

        recorded_off = sampling.ALWAYS_ON.should_sample(
            trace.SpanContext(
                0x000000000000000000000000DEADBEF7,
                0x00000000DEADBEF8,
                trace_options=trace.TraceOptions.RECORDED,
            ),
            0x000000000000000000000000DEADBEF9,
            0x00000000DEADBEFA,
            "unrecorded parent, sampling off",
        )
        self.assertTrue(recorded_off.sampled)
        self.assertEqual(recorded_off.attributes, {})
