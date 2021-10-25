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
from abc import abstractmethod
from unittest.mock import Mock

import opentelemetry.trace as trace_api
from opentelemetry.context import Context, get_current
from opentelemetry.propagators.b3 import (  # pylint: disable=no-name-in-module,import-error
    B3MultiFormat,
    B3SingleFormat,
)
from opentelemetry.propagators.textmap import DefaultGetter
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import id_generator
from opentelemetry.trace.propagation import _SPAN_KEY


def get_child_parent_new_carrier(old_carrier, propagator):

    ctx = propagator.extract(old_carrier)
    parent_span_context = trace_api.get_current_span(ctx).get_span_context()

    parent = trace._Span("parent", parent_span_context)
    child = trace._Span(
        "child",
        trace_api.SpanContext(
            parent_span_context.trace_id,
            id_generator.RandomIdGenerator().generate_span_id(),
            is_remote=False,
            trace_flags=parent_span_context.trace_flags,
            trace_state=parent_span_context.trace_state,
        ),
        parent=parent.get_span_context(),
    )

    new_carrier = {}
    ctx = trace_api.set_span_in_context(child)
    propagator.inject(new_carrier, context=ctx)

    return child, parent, new_carrier


class AbstractB3FormatTestCase:
    # pylint: disable=too-many-public-methods,no-member,invalid-name

    @classmethod
    def setUpClass(cls):
        generator = id_generator.RandomIdGenerator()
        cls.serialized_trace_id = trace_api.format_trace_id(
            generator.generate_trace_id()
        )
        cls.serialized_span_id = trace_api.format_span_id(
            generator.generate_span_id()
        )

    def setUp(self) -> None:
        tracer_provider = trace.TracerProvider()
        patcher = unittest.mock.patch.object(
            trace_api, "get_tracer_provider", return_value=tracer_provider
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def get_child_parent_new_carrier(cls, old_carrier):
        return get_child_parent_new_carrier(old_carrier, cls.get_propagator())

    @classmethod
    @abstractmethod
    def get_propagator(cls):
        pass

    @classmethod
    @abstractmethod
    def get_trace_id(cls, carrier):
        pass

    def assertSampled(self, carrier):
        pass

    def assertNotSampled(self, carrier):
        pass

    def test_extract_multi_header(self):
        """Test the extraction of B3 headers."""
        propagator = self.get_propagator()
        context = {
            propagator.TRACE_ID_KEY: self.serialized_trace_id,
            propagator.SPAN_ID_KEY: self.serialized_span_id,
            propagator.SAMPLED_KEY: "1",
        }
        child, parent, _ = self.get_child_parent_new_carrier(context)

        self.assertEqual(
            context[propagator.TRACE_ID_KEY],
            trace_api.format_trace_id(child.context.trace_id),
        )

        self.assertEqual(
            context[propagator.SPAN_ID_KEY],
            trace_api.format_span_id(child.parent.span_id),
        )
        self.assertTrue(parent.context.is_remote)
        self.assertTrue(parent.context.trace_flags.sampled)

    def test_extract_single_header(self):
        """Test the extraction from a single b3 header."""
        propagator = self.get_propagator()
        child, parent, _ = self.get_child_parent_new_carrier(
            {
                propagator.SINGLE_HEADER_KEY: f"{self.serialized_trace_id}-{self.serialized_span_id}"
            }
        )

        self.assertEqual(
            self.serialized_trace_id,
            trace_api.format_trace_id(child.context.trace_id),
        )
        self.assertEqual(
            self.serialized_span_id,
            trace_api.format_span_id(child.parent.span_id),
        )
        self.assertTrue(parent.context.is_remote)
        self.assertTrue(parent.context.trace_flags.sampled)

        child, parent, _ = self.get_child_parent_new_carrier(
            {
                propagator.SINGLE_HEADER_KEY: f"{self.serialized_trace_id}-{self.serialized_span_id}-1"
            }
        )

        self.assertEqual(
            self.serialized_trace_id,
            trace_api.format_trace_id(child.context.trace_id),
        )
        self.assertEqual(
            self.serialized_span_id,
            trace_api.format_span_id(child.parent.span_id),
        )

        self.assertTrue(parent.context.is_remote)
        self.assertTrue(parent.context.trace_flags.sampled)

    def test_extract_header_precedence(self):
        """A single b3 header should take precedence over multiple
        headers.
        """
        propagator = self.get_propagator()
        single_header_trace_id = self.serialized_trace_id[:-3] + "123"

        _, _, new_carrier = self.get_child_parent_new_carrier(
            {
                propagator.SINGLE_HEADER_KEY: f"{single_header_trace_id}-{self.serialized_span_id}",
                propagator.TRACE_ID_KEY: self.serialized_trace_id,
                propagator.SPAN_ID_KEY: self.serialized_span_id,
                propagator.SAMPLED_KEY: "1",
            }
        )

        self.assertEqual(
            self.get_trace_id(new_carrier), single_header_trace_id
        )

    def test_enabled_sampling(self):
        """Test b3 sample key variants that turn on sampling."""
        propagator = self.get_propagator()
        for variant in ["1", "True", "true", "d"]:
            _, _, new_carrier = self.get_child_parent_new_carrier(
                {
                    propagator.TRACE_ID_KEY: self.serialized_trace_id,
                    propagator.SPAN_ID_KEY: self.serialized_span_id,
                    propagator.SAMPLED_KEY: variant,
                }
            )
            self.assertSampled(new_carrier)

    def test_disabled_sampling(self):
        """Test b3 sample key variants that turn off sampling."""
        propagator = self.get_propagator()
        for variant in ["0", "False", "false", None]:
            _, _, new_carrier = self.get_child_parent_new_carrier(
                {
                    propagator.TRACE_ID_KEY: self.serialized_trace_id,
                    propagator.SPAN_ID_KEY: self.serialized_span_id,
                    propagator.SAMPLED_KEY: variant,
                }
            )
            self.assertNotSampled(new_carrier)

    def test_flags(self):
        """x-b3-flags set to "1" should result in propagation."""
        propagator = self.get_propagator()
        _, _, new_carrier = self.get_child_parent_new_carrier(
            {
                propagator.TRACE_ID_KEY: self.serialized_trace_id,
                propagator.SPAN_ID_KEY: self.serialized_span_id,
                propagator.FLAGS_KEY: "1",
            }
        )

        self.assertSampled(new_carrier)

    def test_flags_and_sampling(self):
        """Propagate if b3 flags and sampling are set."""
        propagator = self.get_propagator()
        _, _, new_carrier = self.get_child_parent_new_carrier(
            {
                propagator.TRACE_ID_KEY: self.serialized_trace_id,
                propagator.SPAN_ID_KEY: self.serialized_span_id,
                propagator.FLAGS_KEY: "1",
            }
        )

        self.assertSampled(new_carrier)

    def test_derived_ctx_is_returned_for_success(self):
        """Ensure returned context is derived from the given context."""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()
        new_ctx = propagator.extract(
            {
                propagator.TRACE_ID_KEY: self.serialized_trace_id,
                propagator.SPAN_ID_KEY: self.serialized_span_id,
                propagator.FLAGS_KEY: "1",
            },
            old_ctx,
        )
        self.assertIn(_SPAN_KEY, new_ctx)
        for key, value in old_ctx.items():  # pylint:disable=no-member
            self.assertIn(key, new_ctx)
            # pylint:disable=unsubscriptable-object
            self.assertEqual(new_ctx[key], value)

    def test_derived_ctx_is_returned_for_failure(self):
        """Ensure returned context is derived from the given context."""
        old_ctx = Context({"k2": "v2"})
        new_ctx = self.get_propagator().extract({}, old_ctx)
        self.assertNotIn(_SPAN_KEY, new_ctx)
        for key, value in old_ctx.items():  # pylint:disable=no-member
            self.assertIn(key, new_ctx)
            # pylint:disable=unsubscriptable-object
            self.assertEqual(new_ctx[key], value)

    def test_64bit_trace_id(self):
        """64 bit trace ids should be padded to 128 bit trace ids."""
        propagator = self.get_propagator()
        trace_id_64_bit = self.serialized_trace_id[:16]

        _, _, new_carrier = self.get_child_parent_new_carrier(
            {
                propagator.TRACE_ID_KEY: trace_id_64_bit,
                propagator.SPAN_ID_KEY: self.serialized_span_id,
                propagator.FLAGS_KEY: "1",
            },
        )

        self.assertEqual(
            self.get_trace_id(new_carrier), "0" * 16 + trace_id_64_bit
        )

    def test_extract_invalid_single_header_to_explicit_ctx(self):
        """Given unparsable header, do not modify context"""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()

        carrier = {propagator.SINGLE_HEADER_KEY: "0-1-2-3-4-5-6-7"}
        new_ctx = propagator.extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_invalid_single_header_to_implicit_ctx(self):
        propagator = self.get_propagator()
        carrier = {propagator.SINGLE_HEADER_KEY: "0-1-2-3-4-5-6-7"}
        new_ctx = propagator.extract(carrier)

        self.assertDictEqual(Context(), new_ctx)

    def test_extract_missing_trace_id_to_explicit_ctx(self):
        """Given no trace ID, do not modify context"""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()

        carrier = {
            propagator.SPAN_ID_KEY: self.serialized_span_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_missing_trace_id_to_implicit_ctx(self):
        propagator = self.get_propagator()
        carrier = {
            propagator.SPAN_ID_KEY: self.serialized_span_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier)

        self.assertDictEqual(Context(), new_ctx)

    def test_extract_invalid_trace_id_to_explicit_ctx(self):
        """Given invalid trace ID, do not modify context"""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()

        carrier = {
            propagator.TRACE_ID_KEY: "abc123",
            propagator.SPAN_ID_KEY: self.serialized_span_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_invalid_trace_id_to_implicit_ctx(self):
        propagator = self.get_propagator()
        carrier = {
            propagator.TRACE_ID_KEY: "abc123",
            propagator.SPAN_ID_KEY: self.serialized_span_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier)

        self.assertDictEqual(Context(), new_ctx)

    def test_extract_invalid_span_id_to_explicit_ctx(self):
        """Given invalid span ID, do not modify context"""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()

        carrier = {
            propagator.TRACE_ID_KEY: self.serialized_trace_id,
            propagator.SPAN_ID_KEY: "abc123",
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_invalid_span_id_to_implicit_ctx(self):
        propagator = self.get_propagator()
        carrier = {
            propagator.TRACE_ID_KEY: self.serialized_trace_id,
            propagator.SPAN_ID_KEY: "abc123",
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier)

        self.assertDictEqual(Context(), new_ctx)

    def test_extract_missing_span_id_to_explicit_ctx(self):
        """Given no span ID, do not modify context"""
        old_ctx = Context({"k1": "v1"})
        propagator = self.get_propagator()

        carrier = {
            propagator.TRACE_ID_KEY: self.serialized_trace_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_missing_span_id_to_implicit_ctx(self):
        propagator = self.get_propagator()
        carrier = {
            propagator.TRACE_ID_KEY: self.serialized_trace_id,
            propagator.FLAGS_KEY: "1",
        }
        new_ctx = propagator.extract(carrier)

        self.assertDictEqual(Context(), new_ctx)

    def test_extract_empty_carrier_to_explicit_ctx(self):
        """Given no headers at all, do not modify context"""
        old_ctx = Context({"k1": "v1"})

        carrier = {}
        new_ctx = self.get_propagator().extract(carrier, old_ctx)

        self.assertDictEqual(new_ctx, old_ctx)

    def test_extract_empty_carrier_to_implicit_ctx(self):
        new_ctx = self.get_propagator().extract({})
        self.assertDictEqual(Context(), new_ctx)

    def test_inject_empty_context(self):
        """If the current context has no span, don't add headers"""
        new_carrier = {}
        self.get_propagator().inject(new_carrier, get_current())
        assert len(new_carrier) == 0

    def test_default_span(self):
        """Make sure propagator does not crash when working with NonRecordingSpan"""

        class CarrierGetter(DefaultGetter):
            def get(self, carrier, key):
                return carrier.get(key, None)

        propagator = self.get_propagator()
        ctx = propagator.extract({}, getter=CarrierGetter())
        propagator.inject({}, context=ctx)

    def test_fields(self):
        """Make sure the fields attribute returns the fields used in inject"""

        propagator = self.get_propagator()
        tracer = trace.TracerProvider().get_tracer("sdk_tracer_provider")

        mock_setter = Mock()

        with tracer.start_as_current_span("parent"):
            with tracer.start_as_current_span("child"):
                propagator.inject({}, setter=mock_setter)

        inject_fields = set()

        for call in mock_setter.mock_calls:
            inject_fields.add(call[1][1])

        self.assertEqual(propagator.fields, inject_fields)

    def test_extract_none_context(self):
        """Given no trace ID, do not modify context"""
        old_ctx = None

        carrier = {}
        new_ctx = self.get_propagator().extract(carrier, old_ctx)
        self.assertDictEqual(Context(), new_ctx)


class TestB3MultiFormat(AbstractB3FormatTestCase, unittest.TestCase):
    @classmethod
    def get_propagator(cls):
        return B3MultiFormat()

    @classmethod
    def get_trace_id(cls, carrier):
        return carrier[cls.get_propagator().TRACE_ID_KEY]

    def assertSampled(self, carrier):
        self.assertEqual(carrier[self.get_propagator().SAMPLED_KEY], "1")

    def assertNotSampled(self, carrier):
        self.assertEqual(carrier[self.get_propagator().SAMPLED_KEY], "0")


class TestB3SingleFormat(AbstractB3FormatTestCase, unittest.TestCase):
    @classmethod
    def get_propagator(cls):
        return B3SingleFormat()

    @classmethod
    def get_trace_id(cls, carrier):
        return carrier[cls.get_propagator().SINGLE_HEADER_KEY].split("-")[0]

    def assertSampled(self, carrier):
        self.assertEqual(
            carrier[self.get_propagator().SINGLE_HEADER_KEY].split("-")[2], "1"
        )

    def assertNotSampled(self, carrier):
        self.assertEqual(
            carrier[self.get_propagator().SINGLE_HEADER_KEY].split("-")[2], "0"
        )
