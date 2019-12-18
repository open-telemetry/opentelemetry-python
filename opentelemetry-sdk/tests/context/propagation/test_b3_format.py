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
import opentelemetry.trace as trace_api
from opentelemetry.sdk.trace.propagation.context import from_context

INJECTOR = b3_format.B3Injector
EXTRACTOR = b3_format.B3Extractor


class TestB3Format(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serialized_trace_id = b3_format.format_trace_id(
            trace.generate_trace_id()
        )
        cls.serialized_span_id = b3_format.format_span_id(
            trace.generate_span_id()
        )

    def test_extract_multi_header(self):
        """Test the extraction of B3 headers."""
        carrier = {
            b3_format.TRACE_ID_KEY: self.serialized_trace_id,
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            b3_format.SAMPLED_KEY: "1",
        }
        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(
            new_carrier[b3_format.TRACE_ID_KEY], self.serialized_trace_id
        )
        self.assertEqual(
            new_carrier[b3_format.SPAN_ID_KEY], self.serialized_span_id
        )
        self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "1")

    def test_extract_single_header(self):
        """Test the extraction from a single b3 header."""
        carrier = {
            EXTRACTOR.SINGLE_HEADER_KEY: "{}-{}".format(
                self.serialized_trace_id, self.serialized_span_id
            )
        }
        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(
            new_carrier[b3_format.TRACE_ID_KEY], self.serialized_trace_id
        )
        self.assertEqual(
            new_carrier[b3_format.SPAN_ID_KEY], self.serialized_span_id
        )
        self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "1")

    def test_extract_header_precedence(self):
        """A single b3 header should take precedence over multiple
        headers.
        """
        single_header_trace_id = self.serialized_trace_id[:-3] + "123"
        carrier = {
            EXTRACTOR.SINGLE_HEADER_KEY: "{}-{}".format(
                single_header_trace_id, self.serialized_span_id
            ),
            b3_format.TRACE_ID_KEY: self.serialized_trace_id,
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            b3_format.SAMPLED_KEY: "1",
        }
        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(
            new_carrier[b3_format.TRACE_ID_KEY], single_header_trace_id
        )

    def test_enabled_sampling(self):
        """Test b3 sample key variants that turn on sampling."""
        for variant in ["1", "True", "true", "d"]:
            carrier = {
                b3_format.TRACE_ID_KEY: self.serialized_trace_id,
                b3_format.SPAN_ID_KEY: self.serialized_span_id,
                b3_format.SAMPLED_KEY: variant,
            }
            EXTRACTOR.extract(carrier)
            new_carrier = {}
            INJECTOR.inject(
                new_carrier, set_in_carrier=dict.__setitem__,
            )
            self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "1")

    def test_disabled_sampling(self):
        """Test b3 sample key variants that turn off sampling."""
        for variant in ["0", "False", "false", None]:
            carrier = {
                b3_format.TRACE_ID_KEY: self.serialized_trace_id,
                b3_format.SPAN_ID_KEY: self.serialized_span_id,
                b3_format.SAMPLED_KEY: variant,
            }
            EXTRACTOR.extract(carrier)
            new_carrier = {}
            INJECTOR.inject(
                new_carrier, set_in_carrier=dict.__setitem__,
            )
            self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "0")

    def test_flags(self):
        """x-b3-flags set to "1" should result in propagation."""
        carrier = {
            b3_format.TRACE_ID_KEY: self.serialized_trace_id,
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            EXTRACTOR.FLAGS_KEY: "1",
        }

        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "1")

    def test_flags_and_sampling(self):
        """Propagate if b3 flags and sampling are set."""
        carrier = {
            b3_format.TRACE_ID_KEY: self.serialized_trace_id,
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            EXTRACTOR.FLAGS_KEY: "1",
        }
        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(new_carrier[b3_format.SAMPLED_KEY], "1")

    def test_64bit_trace_id(self):
        """64 bit trace ids should be padded to 128 bit trace ids."""
        trace_id_64_bit = self.serialized_trace_id[:16]
        carrier = {
            b3_format.TRACE_ID_KEY: trace_id_64_bit,
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            EXTRACTOR.FLAGS_KEY: "1",
        }
        EXTRACTOR.extract(carrier)
        new_carrier = {}
        INJECTOR.inject(
            new_carrier, set_in_carrier=dict.__setitem__,
        )
        self.assertEqual(
            new_carrier[b3_format.TRACE_ID_KEY], "0" * 16 + trace_id_64_bit
        )

    def test_invalid_single_header(self):
        """If an invalid single header is passed, return an
        invalid SpanContext.
        """
        carrier = {EXTRACTOR.SINGLE_HEADER_KEY: "0-1-2-3-4-5-6-7"}
        span_context = from_context(EXTRACTOR.extract(carrier))
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)

    def test_missing_trace_id(self):
        """If a trace id is missing, populate an invalid trace id."""
        carrier = {
            b3_format.SPAN_ID_KEY: self.serialized_span_id,
            EXTRACTOR.FLAGS_KEY: "1",
        }
        span_context = from_context(EXTRACTOR.extract(carrier))
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)

    def test_missing_span_id(self):
        """If a trace id is missing, populate an invalid trace id."""
        carrier = {
            b3_format.TRACE_ID_KEY: self.serialized_trace_id,
            EXTRACTOR.FLAGS_KEY: "1",
        }
        span_context = from_context(EXTRACTOR.extract(carrier))
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)
