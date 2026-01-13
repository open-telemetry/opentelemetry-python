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

# type: ignore

import os
import unittest
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.baggage import get_all, set_baggage
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context, get_current
from opentelemetry.propagators._envcarrier import (
    EnvironmentGetter,
    EnvironmentSetter,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestEnvironmentGetter(unittest.TestCase):
    """Unit tests for EnvironmentGetter."""

    def test_get_existing_env_var(self):
        """Test retrieving an existing environment variable."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            result = getter.get({}, "test_key")
            self.assertEqual(result, ["test_value"])

    def test_get_case_insensitive(self):
        """Test case insensitive lookup for environment variables."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            self.assertEqual(getter.get({}, "test_key"), ["test_value"])
            self.assertEqual(getter.get({}, "TEST_KEY"), ["test_value"])
            self.assertEqual(getter.get({}, "Test_Key"), ["test_value"])

    def test_get_nonexistent_env_var(self):
        """Test retrieving a non-existent environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            result = getter.get({}, "nonexistent_key")
            self.assertIsNone(result)

    def test_get_empty_value(self):
        """Test retrieving an environment variable with empty value."""
        with patch.dict(os.environ, {"EMPTY_KEY": ""}):
            getter = EnvironmentGetter()
            result = getter.get({}, "empty_key")
            self.assertEqual(result, [""])

    def test_get_with_special_characters(self):
        """Test environment variables with special characters."""
        with patch.dict(
            os.environ, {"TEST_KEY": "value with spaces and !@#$%"}
        ):
            getter = EnvironmentGetter()
            result = getter.get({}, "test_key")
            self.assertEqual(result, ["value with spaces and !@#$%"])

    def test_keys(self):
        """Test getting all environment variable keys."""
        test_env = {"KEY1": "value1", "KEY2": "value2", "key3": "value3"}
        with patch.dict(os.environ, test_env, clear=True):
            getter = EnvironmentGetter()
            keys = getter.keys({})
            expected_keys = {"key1", "key2", "key3"}
            self.assertEqual(set(keys), expected_keys)

    def test_keys_empty_environment(self):
        """Test getting keys when environment is empty."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            keys = getter.keys({})
            self.assertEqual(keys, [])

    def test_uses_snapshot_not_carrier_parameter(self):
        """Test that getter uses internal snapshot, not carrier parameter.

        The carrier parameter exists for interface compatibility with
        Getter[CarrierT], but EnvironmentGetter reads from os.environ at
        initialization, creating an immutable snapshot.
        """
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            # Both return same value from snapshot, carrier is ignored
            result1 = getter.get({}, "test_key")
            result2 = getter.get({"test_key": "different"}, "test_key")
            self.assertEqual(result1, ["test_value"])
            self.assertEqual(result2, ["test_value"])

    def test_snapshot_immutability(self):
        """Test that getter snapshot doesn't see changes after initialization."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            self.assertIsNone(getter.get({}, "test_key"))

            # Add environment variable after initialization
            os.environ["TEST_KEY"] = "new_value"

            # Getter should still not see the new value
            self.assertIsNone(getter.get({}, "test_key"))


class TestEnvironmentSetter(unittest.TestCase):
    """Unit tests for EnvironmentSetter."""

    def test_set_basic(self):
        """Test setting a value in carrier dictionary."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "test_key", "test_value")
        self.assertEqual(carrier, {"TEST_KEY": "test_value"})

    def test_set_multiple_values(self):
        """Test setting multiple values in the same carrier."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "key1", "value1")
        setter.set(carrier, "key2", "value2")
        setter.set(carrier, "key3", "value3")
        expected = {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}
        self.assertEqual(carrier, expected)

    def test_set_overwrites_existing(self):
        """Test that setting a key overwrites existing value."""
        setter = EnvironmentSetter()
        carrier = {"TEST_KEY": "old_value"}
        setter.set(carrier, "test_key", "new_value")
        self.assertEqual(carrier, {"TEST_KEY": "new_value"})

    def test_set_uppercases_keys(self):
        """Test that keys are normalized to uppercase."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "lowercase_key", "value1")
        setter.set(carrier, "UPPERCASE_KEY", "value2")
        setter.set(carrier, "MiXeD_cAsE_kEy", "value3")
        expected = {
            "LOWERCASE_KEY": "value1",
            "UPPERCASE_KEY": "value2",
            "MIXED_CASE_KEY": "value3",
        }
        self.assertEqual(carrier, expected)

    def test_set_special_characters_in_value(self):
        """Test setting values with special characters."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "test_key", "value with spaces and !@#$%^&*()")
        self.assertEqual(
            carrier, {"TEST_KEY": "value with spaces and !@#$%^&*()"}
        )

    def test_set_empty_value(self):
        """Test setting an empty value."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "empty_key", "")
        self.assertEqual(carrier, {"EMPTY_KEY": ""})

    def test_does_not_modify_os_environ(self):
        """Test that setter does not modify os.environ."""
        setter = EnvironmentSetter()
        carrier = {}
        original_environ = dict(os.environ)
        setter.set(carrier, "test_key", "test_value")
        self.assertEqual(dict(os.environ), original_environ)
        self.assertEqual(carrier, {"TEST_KEY": "test_value"})


class TestEnvironmentCarrierWithTraceContext(unittest.TestCase):
    """Integration tests with W3C TraceContext propagator."""

    TRACE_ID = 0x4BF92F3577B34DA6A3CE929D0E0E4736
    SPAN_ID = 0x00F067AA0BA902B7

    def setUp(self):
        self.propagator = TraceContextTextMapPropagator()

    def _extract_with_env(self, env_vars):
        """Helper: Extract context from environment variables."""
        with patch.dict(os.environ, env_vars, clear=True):
            getter = EnvironmentGetter()
            return self.propagator.extract({}, getter=getter)

    def _inject_to_env(self, context):
        """Helper: Inject context into environment dict."""
        setter = EnvironmentSetter()
        env_dict = {}
        self.propagator.inject(env_dict, context=context, setter=setter)
        return env_dict

    def test_extract_valid_traceparent(self):
        """Test extracting valid traceparent from environment."""
        traceparent = f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01"
        ctx = self._extract_with_env({"TRACEPARENT": traceparent})

        span_context = trace.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)
        self.assertTrue(span_context.trace_flags.sampled)
        self.assertTrue(span_context.is_remote)

    def test_extract_traceparent_not_sampled(self):
        """Test extracting traceparent with sampled=false."""
        traceparent = f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-00"
        ctx = self._extract_with_env({"TRACEPARENT": traceparent})

        span_context = trace.get_current_span(ctx).get_span_context()
        self.assertFalse(span_context.trace_flags.sampled)

    def test_extract_with_tracestate(self):
        """Test extracting traceparent with tracestate."""
        traceparent = f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01"
        tracestate = "vendor1=value1,vendor2=value2"

        ctx = self._extract_with_env(
            {"TRACEPARENT": traceparent, "TRACESTATE": tracestate}
        )

        span_context = trace.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_state.get("vendor1"), "value1")
        self.assertEqual(span_context.trace_state.get("vendor2"), "value2")

    def test_extract_invalid_traceparent(self):
        """Test that invalid traceparent formats are handled gracefully.

        Per W3C Trace Context spec, invalid traceparent should be ignored.
        """
        invalid_traceparents = [
            "invalid-format",
            "00-00000000000000000000000000000000-1234567890123456-00",  # zero trace_id
            "00-12345678901234567890123456789012-0000000000000000-00",  # zero span_id
            "00-12345678901234567890123456789012-1234567890123456-00-extra",  # extra data
        ]

        for invalid_tp in invalid_traceparents:
            with self.subTest(traceparent=invalid_tp):
                ctx = self._extract_with_env({"TRACEPARENT": invalid_tp})
                span = trace.get_current_span(ctx)
                self.assertEqual(
                    span.get_span_context(), trace.INVALID_SPAN_CONTEXT
                )

    def test_extract_missing_traceparent(self):
        """Test extraction with missing TRACEPARENT."""
        ctx = self._extract_with_env({})
        span = trace.get_current_span(ctx)
        self.assertIsInstance(span.get_span_context(), trace.SpanContext)

    def test_extract_preserves_context_on_invalid_traceparent(self):
        """Test that invalid traceparent preserves original context."""
        orig_ctx = Context({"my_key": "my_value"})

        with patch.dict(os.environ, {"TRACEPARENT": "invalid"}, clear=True):
            getter = EnvironmentGetter()
            ctx = self.propagator.extract(
                {}, context=orig_ctx, getter=getter
            )

        self.assertDictEqual(ctx, orig_ctx)

    def test_inject_valid_span_context(self):
        """Test injecting valid span context to environment dict."""
        span_context = trace.SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=trace.TraceFlags(0x01),
        )
        ctx = trace.set_span_in_context(trace.NonRecordingSpan(span_context))

        env_dict = self._inject_to_env(ctx)

        expected_traceparent = (
            f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01"
        )
        self.assertEqual(env_dict["TRACEPARENT"], expected_traceparent)

    def test_inject_does_not_include_empty_tracestate(self):
        """Test that empty tracestate is not injected.

        Per W3C spec: vendors SHOULD avoid sending empty tracestate.
        """
        span_context = trace.SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
        )
        ctx = trace.set_span_in_context(trace.NonRecordingSpan(span_context))

        env_dict = self._inject_to_env(ctx)

        self.assertIn("TRACEPARENT", env_dict)
        self.assertNotIn("TRACESTATE", env_dict)

    def test_inject_invalid_context(self):
        """Test that invalid context is not propagated."""
        ctx = trace.set_span_in_context(trace.INVALID_SPAN)
        env_dict = self._inject_to_env(ctx)
        self.assertNotIn("TRACEPARENT", env_dict)

    def test_roundtrip_preserves_traceparent(self):
        """Test that traceparent survives extract->inject->extract cycle."""
        original_traceparent = (
            f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01"
        )

        # Extract from environment
        ctx1 = self._extract_with_env({"TRACEPARENT": original_traceparent})

        # Inject to new environment dict
        env_dict = self._inject_to_env(ctx1)
        self.assertEqual(env_dict["TRACEPARENT"], original_traceparent)

        # Extract again from injected dict
        ctx2 = self._extract_with_env(env_dict)

        # Verify both contexts have same span context
        span1 = trace.get_current_span(ctx1).get_span_context()
        span2 = trace.get_current_span(ctx2).get_span_context()
        self.assertEqual(span1.trace_id, span2.trace_id)
        self.assertEqual(span1.span_id, span2.span_id)
        self.assertEqual(span1.trace_flags, span2.trace_flags)

    def test_roundtrip_preserves_tracestate(self):
        """Test that tracestate survives roundtrip."""
        env_vars = {
            "TRACEPARENT": f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01",
            "TRACESTATE": "vendor1=value1,vendor2=value2",
        }

        ctx1 = self._extract_with_env(env_vars)
        env_dict = self._inject_to_env(ctx1)

        self.assertIn("TRACESTATE", env_dict)
        self.assertIn("vendor1=value1", env_dict["TRACESTATE"])
        self.assertIn("vendor2=value2", env_dict["TRACESTATE"])

    def test_case_handling(self):
        """Test case handling for W3C headers."""
        test_env = {
            "TRACEPARENT": f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01",
            "TRACESTATE": "vendor=value",
        }

        with patch.dict(os.environ, test_env, clear=True):
            getter = EnvironmentGetter()
            # Propagator uses lowercase keys
            self.assertIsNotNone(getter.get({}, "traceparent"))
            self.assertIsNotNone(getter.get({}, "tracestate"))

    @patch("opentelemetry.trace.INVALID_SPAN_CONTEXT")
    @patch("opentelemetry.trace.get_current_span")
    def test_fields(self, mock_get_current_span, mock_invalid_span_context):
        """Test that propagator.fields matches injected keys."""
        from opentelemetry.trace.span import TraceState

        mock_get_current_span.configure_mock(
            return_value=Mock(
                **{
                    "get_span_context.return_value": Mock(
                        **{
                            "trace_id": 1,
                            "span_id": 2,
                            "trace_flags": 3,
                            "trace_state": TraceState([("a", "b")]),
                        }
                    )
                }
            )
        )

        mock_setter = Mock()
        self.propagator.inject({}, setter=mock_setter)

        inject_fields = set()
        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, self.propagator.fields)


class TestEnvironmentCarrierWithBaggage(unittest.TestCase):
    """Integration tests with W3C Baggage propagator."""

    def setUp(self):
        self.propagator = W3CBaggagePropagator()

    def _extract_with_env(self, env_vars):
        """Helper: Extract baggage from environment variables."""
        with patch.dict(os.environ, env_vars, clear=True):
            getter = EnvironmentGetter()
            return self.propagator.extract({}, getter=getter)

    def _inject_to_env(self, context):
        """Helper: Inject baggage into environment dict."""
        setter = EnvironmentSetter()
        env_dict = {}
        self.propagator.inject(env_dict, context=context, setter=setter)
        return env_dict

    def test_extract_baggage(self):
        """Test extracting baggage from BAGGAGE environment variable."""
        ctx = self._extract_with_env(
            {"BAGGAGE": "key1=value1,key2=value2,key3=value3"}
        )

        baggage = get_all(ctx)
        self.assertEqual(
            baggage, {"key1": "value1", "key2": "value2", "key3": "value3"}
        )

    def test_extract_empty_baggage(self):
        """Test extracting empty baggage."""
        ctx = self._extract_with_env({"BAGGAGE": ""})
        baggage = get_all(ctx)
        self.assertEqual(baggage, {})

    def test_extract_missing_baggage(self):
        """Test extraction with missing BAGGAGE."""
        ctx = self._extract_with_env({})
        baggage = get_all(ctx)
        self.assertEqual(baggage, {})

    def test_inject_baggage(self):
        """Test injecting baggage into environment dict."""
        ctx = get_current()
        ctx = set_baggage("deployment", "production", context=ctx)
        ctx = set_baggage("service", "api-gateway", context=ctx)

        env_dict = self._inject_to_env(ctx)

        self.assertIn("BAGGAGE", env_dict)
        baggage_value = env_dict["BAGGAGE"]
        self.assertIn("deployment=production", baggage_value)
        self.assertIn("service=api-gateway", baggage_value)

    def test_inject_no_baggage(self):
        """Test that empty baggage is not injected."""
        ctx = get_current()
        env_dict = self._inject_to_env(ctx)
        self.assertNotIn("BAGGAGE", env_dict)

    def test_roundtrip_baggage(self):
        """Test baggage roundtrip."""
        ctx1 = get_current()
        ctx1 = set_baggage("user_id", "12345", context=ctx1)
        ctx1 = set_baggage("session_id", "abc-def", context=ctx1)

        env_dict = self._inject_to_env(ctx1)
        ctx2 = self._extract_with_env(env_dict)

        baggage1 = get_all(ctx1)
        baggage2 = get_all(ctx2)
        self.assertEqual(baggage1, baggage2)

    @patch("opentelemetry.baggage.propagation.get_all")
    @patch("opentelemetry.baggage.propagation._format_baggage")
    def test_fields(self, mock_format_baggage, mock_get_all):
        """Test that propagator.fields matches injected keys."""
        mock_setter = Mock()
        self.propagator.inject({}, setter=mock_setter)

        inject_fields = set()
        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, self.propagator.fields)


class TestEnvironmentCarrierWithCompositePropagator(unittest.TestCase):
    """Integration tests with multiple propagators."""

    TRACE_ID = 0x4BF92F3577B34DA6A3CE929D0E0E4736
    SPAN_ID = 0x00F067AA0BA902B7

    def setUp(self):
        from opentelemetry.propagators.composite import CompositePropagator

        self.propagator = CompositePropagator(
            [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
        )

    def test_extract_all_w3c_headers(self):
        """Test extracting both traceparent and baggage."""
        env_vars = {
            "TRACEPARENT": f"00-{self.TRACE_ID:032x}-{self.SPAN_ID:016x}-01",
            "TRACESTATE": "vendor=value",
            "BAGGAGE": "user_id=12345,session_id=abc-def",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            getter = EnvironmentGetter()
            ctx = self.propagator.extract({}, getter=getter)

        # Verify traceparent was extracted
        span_context = trace.get_current_span(ctx).get_span_context()
        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)

        # Verify baggage was extracted
        baggage = get_all(ctx)
        self.assertEqual(baggage["user_id"], "12345")
        self.assertEqual(baggage["session_id"], "abc-def")

    def test_inject_all_w3c_headers(self):
        """Test injecting both traceparent and baggage."""
        span_context = trace.SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=trace.TraceFlags(0x01),
        )
        ctx = trace.set_span_in_context(trace.NonRecordingSpan(span_context))
        ctx = set_baggage("deployment", "production", context=ctx)

        setter = EnvironmentSetter()
        env_dict = {}
        self.propagator.inject(env_dict, context=ctx, setter=setter)

        # Verify both were injected with uppercase keys
        self.assertIn("TRACEPARENT", env_dict)
        self.assertIn("BAGGAGE", env_dict)
        self.assertIn("deployment=production", env_dict["BAGGAGE"])

    def test_empty_environment(self):
        """Test behavior with completely empty environment."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            ctx = self.propagator.extract({}, getter=getter)

            # Should not crash, return valid context
            self.assertIsInstance(ctx, Context)


if __name__ == "__main__":
    unittest.main()
