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
import opentelemetry.sdk.context.propagation.b3_format as b3_format
import opentelemetry.sdk.trace as trace

FORMAT = b3_format.B3Format()


def _get_from_dict(carrier: dict, key: str) -> str:
    return carrier.get(key)


def _set_into_dict(carrier: dict, key: str, value: str):
    carrier[key] = value


class TestB3Format(unittest.TestCase):
    def test_extract_multi_header(self):
        """Test the extraction of B3 headers """
        trace_id = str(trace.generate_trace_id())
        span_id = str(trace.generate_span_id())
        carrier = {
            FORMAT.TRACE_ID_KEY: trace_id,
            FORMAT.SPAN_ID_KEY: span_id,
            FORMAT.SAMPLED_KEY: "1",
        }
        span_context = FORMAT.extract(_get_from_dict, carrier)
        new_carrier = {}
        FORMAT.inject(span_context, _set_into_dict, new_carrier)
        self.assertEqual(new_carrier[FORMAT.TRACE_ID_KEY], trace_id)
        self.assertEqual(new_carrier[FORMAT.SPAN_ID_KEY], span_id)
        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_extract_single_headder(self):
        """Test the extraction from a single b3 header"""
        trace_id = str(trace.generate_trace_id())
        span_id = str(trace.generate_span_id())
        carrier = {FORMAT.SINGLE_HEADER_KEY: "{}-{}".format(trace_id, span_id)}
        span_context = FORMAT.extract(_get_from_dict, carrier)
        new_carrier = {}
        FORMAT.inject(span_context, _set_into_dict, new_carrier)
        self.assertEqual(new_carrier[FORMAT.TRACE_ID_KEY], trace_id)
        self.assertEqual(new_carrier[FORMAT.SPAN_ID_KEY], span_id)
        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")
