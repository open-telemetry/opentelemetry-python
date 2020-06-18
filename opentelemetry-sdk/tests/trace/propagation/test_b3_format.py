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

import unittest

import opentelemetry.sdk.trace as trace
import opentelemetry.sdk.trace.propagation.b3_format as b3_format
import opentelemetry.trace as trace_api
from opentelemetry.context import get_current

FORMAT = b3_format.B3Format()


def get_as_list(dict_object, key):
    value = dict_object.get(key)
    return [value] if value is not None else []


def get_child_parent_new_carrier(old_carrier):

    ctx = FORMAT.extract(get_as_list, old_carrier)
    parent_context = trace_api.get_current_span(ctx).get_context()

    parent = trace.Span("parent", parent_context)
    child = trace.Span(
        "child",
        trace_api.SpanContext(
            parent_context.trace_id,
            trace.generate_span_id(),
            is_remote=False,
            trace_flags=parent_context.trace_flags,
            trace_state=parent_context.trace_state,
        ),
        parent=parent.get_context(),
    )

    new_carrier = {}
    ctx = trace_api.set_span_in_context(child)
    FORMAT.inject(dict.__setitem__, new_carrier, context=ctx)

    return child, parent, new_carrier


class TestB3Format(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serialized_trace_id = b3_format.format_trace_id(
            trace.generate_trace_id()
        )
        cls.serialized_span_id = b3_format.format_span_id(
            trace.generate_span_id()
        )
        cls.serialized_parent_id = b3_format.format_span_id(
            trace.generate_span_id()
        )

    def test_extract_multi_header(self):
        """Test the extraction of B3 headers."""
        child, parent, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                FORMAT.PARENT_SPAN_ID_KEY: self.serialized_parent_id,
                FORMAT.SAMPLED_KEY: "1",
            }
        )

        self.assertEqual(
            new_carrier[FORMAT.TRACE_ID_KEY],
            b3_format.format_trace_id(child.context.trace_id),
        )
        self.assertEqual(
            new_carrier[FORMAT.SPAN_ID_KEY],
            b3_format.format_span_id(child.context.span_id),
        )
        self.assertEqual(
            new_carrier[FORMAT.PARENT_SPAN_ID_KEY],
            b3_format.format_span_id(parent.context.span_id),
        )
        self.assertTrue(parent.context.is_remote)
        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_extract_single_header(self):
        """Test the extraction from a single b3 header."""
        child, parent, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.SINGLE_HEADER_KEY: "{}-{}".format(
                    self.serialized_trace_id, self.serialized_span_id
                )
            }
        )

        self.assertEqual(
            new_carrier[FORMAT.TRACE_ID_KEY],
            b3_format.format_trace_id(child.context.trace_id),
        )
        self.assertEqual(
            new_carrier[FORMAT.SPAN_ID_KEY],
            b3_format.format_span_id(child.context.span_id),
        )
        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")
        self.assertTrue(parent.context.is_remote)

        child, parent, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.SINGLE_HEADER_KEY: "{}-{}-1-{}".format(
                    self.serialized_trace_id,
                    self.serialized_span_id,
                    self.serialized_parent_id,
                )
            }
        )

        self.assertEqual(
            new_carrier[FORMAT.TRACE_ID_KEY],
            b3_format.format_trace_id(child.context.trace_id),
        )
        self.assertEqual(
            new_carrier[FORMAT.SPAN_ID_KEY],
            b3_format.format_span_id(child.context.span_id),
        )
        self.assertEqual(
            new_carrier[FORMAT.PARENT_SPAN_ID_KEY],
            b3_format.format_span_id(parent.context.span_id),
        )
        self.assertTrue(parent.context.is_remote)
        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_extract_header_precedence(self):
        """A single b3 header should take precedence over multiple
        headers.
        """
        single_header_trace_id = self.serialized_trace_id[:-3] + "123"

        _, _, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.SINGLE_HEADER_KEY: "{}-{}".format(
                    single_header_trace_id, self.serialized_span_id
                ),
                FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                FORMAT.SAMPLED_KEY: "1",
            }
        )

        self.assertEqual(
            new_carrier[FORMAT.TRACE_ID_KEY], single_header_trace_id
        )

    def test_enabled_sampling(self):
        """Test b3 sample key variants that turn on sampling."""
        for variant in ["1", "True", "true", "d"]:
            _, _, new_carrier = get_child_parent_new_carrier(
                {
                    FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                    FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                    FORMAT.SAMPLED_KEY: variant,
                }
            )

            self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_disabled_sampling(self):
        """Test b3 sample key variants that turn off sampling."""
        for variant in ["0", "False", "false", None]:
            _, _, new_carrier = get_child_parent_new_carrier(
                {
                    FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                    FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                    FORMAT.SAMPLED_KEY: variant,
                }
            )

            self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "0")

    def test_flags(self):
        """x-b3-flags set to "1" should result in propagation."""
        _, _, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                FORMAT.FLAGS_KEY: "1",
            }
        )

        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_flags_and_sampling(self):
        """Propagate if b3 flags and sampling are set."""
        _, _, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
                FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                FORMAT.FLAGS_KEY: "1",
            }
        )

        self.assertEqual(new_carrier[FORMAT.SAMPLED_KEY], "1")

    def test_64bit_trace_id(self):
        """64 bit trace ids should be padded to 128 bit trace ids."""
        trace_id_64_bit = self.serialized_trace_id[:16]

        _, _, new_carrier = get_child_parent_new_carrier(
            {
                FORMAT.TRACE_ID_KEY: trace_id_64_bit,
                FORMAT.SPAN_ID_KEY: self.serialized_span_id,
                FORMAT.FLAGS_KEY: "1",
            }
        )

        self.assertEqual(
            new_carrier[FORMAT.TRACE_ID_KEY], "0" * 16 + trace_id_64_bit
        )

    def test_invalid_single_header(self):
        """If an invalid single header is passed, return an
        invalid SpanContext.
        """
        carrier = {FORMAT.SINGLE_HEADER_KEY: "0-1-2-3-4-5-6-7"}
        ctx = FORMAT.extract(get_as_list, carrier)
        span_context = trace_api.get_current_span(ctx).get_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)

    def test_missing_trace_id(self):
        """If a trace id is missing, populate an invalid trace id."""
        carrier = {
            FORMAT.SPAN_ID_KEY: self.serialized_span_id,
            FORMAT.FLAGS_KEY: "1",
        }

        ctx = FORMAT.extract(get_as_list, carrier)
        span_context = trace_api.get_current_span(ctx).get_context()
        self.assertEqual(span_context.trace_id, trace_api.INVALID_TRACE_ID)

    def test_missing_span_id(self):
        """If a trace id is missing, populate an invalid trace id."""
        carrier = {
            FORMAT.TRACE_ID_KEY: self.serialized_trace_id,
            FORMAT.FLAGS_KEY: "1",
        }

        ctx = FORMAT.extract(get_as_list, carrier)
        span_context = trace_api.get_current_span(ctx).get_context()
        self.assertEqual(span_context.span_id, trace_api.INVALID_SPAN_ID)

    @staticmethod
    def test_inject_empty_context():
        """If the current context has no span, don't add headers"""
        new_carrier = {}
        FORMAT.inject(dict.__setitem__, new_carrier, get_current())
        assert len(new_carrier) == 0
