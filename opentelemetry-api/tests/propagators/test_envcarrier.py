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

import os
import unittest
from unittest.mock import patch

from opentelemetry.propagators.envcarrier import (
    EnvironmentGetter,
    EnvironmentSetter,
)


class TestEnvironmentGetter(unittest.TestCase):
    def test_get_existing_env_var(self):
        """Test retrieving an existing environment variable."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            result = getter.get({}, "test_key")
            self.assertEqual(result, ["test_value"])

    def test_get_existing_env_var_case_insensitive(self):
        """Test case insensitive lookup for environment variables."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            # Test various case combinations
            self.assertEqual(getter.get({}, "test_key"), ["test_value"])
            self.assertEqual(getter.get({}, "TEST_KEY"), ["test_value"])
            self.assertEqual(getter.get({}, "Test_Key"), ["test_value"])

    def test_get_nonexistent_env_var(self):
        """Test retrieving a non-existent environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            result = getter.get({}, "nonexistent_key")
            self.assertIsNone(result)

    def test_get_empty_env_var(self):
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

            # Keys should be lowercase
            expected_keys = {"key1", "key2", "key3"}
            self.assertEqual(set(keys), expected_keys)

    def test_keys_empty_environment(self):
        """Test getting keys when environment is empty."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            keys = getter.keys({})
            self.assertEqual(keys, [])

    def test_carrier_parameter_ignored(self):
        """Test that the carrier parameter is ignored (maintained for interface compatibility)."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            getter = EnvironmentGetter()
            # Carrier parameter should be ignored
            result1 = getter.get({}, "test_key")
            result2 = getter.get({"test_key": "different_value"}, "test_key")
            result3 = getter.get(None, "test_key")

            # All should return the same value from environment
            self.assertEqual(result1, ["test_value"])
            self.assertEqual(result2, ["test_value"])
            self.assertEqual(result3, ["test_value"])

    def test_snapshot_behavior(self):
        """Test that getter takes a snapshot of environment at initialization."""
        # Start with empty environment
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            # Should be empty initially
            self.assertIsNone(getter.get({}, "test_key"))

            # Add environment variable after initialization
            os.environ["TEST_KEY"] = "new_value"

            # Getter should still not see the new value (snapshot behavior)
            self.assertIsNone(getter.get({}, "test_key"))


class TestEnvironmentSetter(unittest.TestCase):
    def test_set_with_new_carrier(self):
        """Test setting a value with a new carrier dictionary."""
        setter = EnvironmentSetter()
        carrier = {}
        setter.set(carrier, "test_key", "test_value")

        self.assertEqual(carrier, {"TEST_KEY": "test_value"})

    def test_set_with_none_carrier(self):
        """Test setting a value when carrier is None."""
        setter = EnvironmentSetter()
        carrier = None
        setter.set(carrier, "test_key", "test_value")

        # Note: carrier would still be None since Python passes by reference
        # but the method should handle None gracefully
        # This is a limitation of the current interface design

    def test_set_multiple_values(self):
        """Test setting multiple values in the same carrier."""
        setter = EnvironmentSetter()
        carrier = {}

        setter.set(carrier, "key1", "value1")
        setter.set(carrier, "key2", "value2")
        setter.set(carrier, "key3", "value3")

        expected = {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}
        self.assertEqual(carrier, expected)

    def test_set_overwrites_existing_key(self):
        """Test that setting a key overwrites existing value."""
        setter = EnvironmentSetter()
        carrier = {"TEST_KEY": "old_value"}

        setter.set(carrier, "test_key", "new_value")

        self.assertEqual(carrier, {"TEST_KEY": "new_value"})

    def test_set_case_normalization(self):
        """Test that keys are normalized to uppercase."""
        setter = EnvironmentSetter()
        carrier = {}

        # Test various case inputs
        setter.set(carrier, "lowercase_key", "value1")
        setter.set(carrier, "UPPERCASE_KEY", "value2")
        setter.set(carrier, "MiXeD_cAsE_kEy", "value3")

        expected = {
            "LOWERCASE_KEY": "value1",
            "UPPERCASE_KEY": "value2",
            "MIXED_CASE_KEY": "value3",
        }
        self.assertEqual(carrier, expected)

    def test_set_with_special_characters(self):
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
        """Test that setting values does not modify os.environ."""
        setter = EnvironmentSetter()
        carrier = {}

        original_environ = dict(os.environ)
        setter.set(carrier, "test_key", "test_value")

        # os.environ should be unchanged
        self.assertEqual(dict(os.environ), original_environ)
        # But carrier should have the value
        self.assertEqual(carrier, {"TEST_KEY": "test_value"})


class TestEnvironmentCarrierIntegration(unittest.TestCase):
    """Integration tests for EnvironmentGetter and EnvironmentSetter."""

    def test_roundtrip_simple(self):
        """Test basic roundtrip: set with setter, get with getter."""
        # Set up environment
        test_env = {
            "TRACEPARENT": "00-12345678901234567890123456789012-1234567890123456-01"
        }

        with patch.dict(os.environ, test_env, clear=True):
            getter = EnvironmentGetter()
            setter = EnvironmentSetter()

            # Get from environment
            value = getter.get({}, "traceparent")
            self.assertEqual(
                value,
                ["00-12345678901234567890123456789012-1234567890123456-01"],
            )

            # Set to new carrier
            new_carrier = {}
            setter.set(new_carrier, "traceparent", value[0])
            self.assertEqual(
                new_carrier,
                {
                    "TRACEPARENT": "00-12345678901234567890123456789012-1234567890123456-01"
                },
            )

    def test_w3c_headers_case_handling(self):
        """Test proper case handling for W3C standard headers."""
        test_env = {
            "TRACEPARENT": "00-12345678901234567890123456789012-1234567890123456-01",
            "TRACESTATE": "vendor=value",
            "BAGGAGE": "key=value",
        }

        with patch.dict(os.environ, test_env, clear=True):
            getter = EnvironmentGetter()

            # Should be able to retrieve using lowercase (standard HTTP header format)
            self.assertEqual(
                getter.get({}, "traceparent"),
                ["00-12345678901234567890123456789012-1234567890123456-01"],
            )
            self.assertEqual(getter.get({}, "tracestate"), ["vendor=value"])
            self.assertEqual(getter.get({}, "baggage"), ["key=value"])

    def test_empty_environment(self):
        """Test behavior with completely empty environment."""
        with patch.dict(os.environ, {}, clear=True):
            getter = EnvironmentGetter()
            setter = EnvironmentSetter()

            # Getting should return None
            self.assertIsNone(getter.get({}, "any_key"))
            self.assertEqual(getter.keys({}), [])

            # Setting should work normally
            carrier = {}
            setter.set(carrier, "new_key", "new_value")
            self.assertEqual(carrier, {"NEW_KEY": "new_value"})


class TestEnvironmentCarrierWithPropagators(unittest.TestCase):
    """Integration tests demonstrating environment carrier usage with propagators.

    Note: These tests demonstrate usage patterns but don't require actual
    propagator imports since validation is handled at the propagator level.
    """

    def test_w3c_traceparent_pattern(self):
        """Test environment carrier with W3C TraceContext header format."""
        # Simulate W3C TraceContext format
        traceparent = "00-12345678901234567890123456789012-1234567890123456-01"

        with patch.dict(os.environ, {"TRACEPARENT": traceparent}):
            getter = EnvironmentGetter()

            # Propagator would use lowercase key for lookup
            result = getter.get({}, "traceparent")
            self.assertEqual(result, [traceparent])

            # Setter would prepare environment for process spawning
            setter = EnvironmentSetter()
            carrier = {}
            setter.set(carrier, "traceparent", traceparent)
            self.assertEqual(carrier, {"TRACEPARENT": traceparent})

    def test_w3c_baggage_pattern(self):
        """Test environment carrier with W3C Baggage header format."""
        baggage = "key1=value1,key2=value2"

        with patch.dict(os.environ, {"BAGGAGE": baggage}):
            getter = EnvironmentGetter()
            result = getter.get({}, "baggage")
            self.assertEqual(result, [baggage])

            setter = EnvironmentSetter()
            carrier = {}
            setter.set(carrier, "baggage", baggage)
            self.assertEqual(carrier, {"BAGGAGE": baggage})

    def test_multiple_headers_integration(self):
        """Test environment carrier with multiple W3C headers."""
        test_env = {
            "TRACEPARENT": "00-12345678901234567890123456789012-1234567890123456-01",
            "TRACESTATE": "vendor=value",
            "BAGGAGE": "key=value",
        }

        with patch.dict(os.environ, test_env, clear=True):
            getter = EnvironmentGetter()
            setter = EnvironmentSetter()

            # Simulate extraction process
            extracted_data = {}
            for key in ["traceparent", "tracestate", "baggage"]:
                value = getter.get({}, key)
                if value is not None:
                    extracted_data[key] = value[0]

            expected = {
                "traceparent": "00-12345678901234567890123456789012-1234567890123456-01",
                "tracestate": "vendor=value",
                "baggage": "key=value",
            }
            self.assertEqual(extracted_data, expected)

            # Simulate injection process
            carrier = {}
            for key, value in extracted_data.items():
                setter.set(carrier, key, value)

            expected_carrier = {
                "TRACEPARENT": "00-12345678901234567890123456789012-1234567890123456-01",
                "TRACESTATE": "vendor=value",
                "BAGGAGE": "key=value",
            }
            self.assertEqual(carrier, expected_carrier)

    def test_carrier_interface_compliance(self):
        """Test that environment carriers comply with the TextMap interfaces."""
        getter = EnvironmentGetter()
        setter = EnvironmentSetter()

        # Test getter interface compliance
        self.assertTrue(hasattr(getter, "get"))
        self.assertTrue(hasattr(getter, "keys"))
        self.assertTrue(callable(getter.get))
        self.assertTrue(callable(getter.keys))

        # Test setter interface compliance
        self.assertTrue(hasattr(setter, "set"))
        self.assertTrue(callable(setter.set))

        # Test method signatures work as expected
        with patch.dict(os.environ, {"TEST": "value"}):
            getter = EnvironmentGetter()

            # get() should accept carrier and key parameters
            result = getter.get({}, "test")
            self.assertEqual(result, ["value"])

            # keys() should accept carrier parameter
            keys = getter.keys({})
            self.assertIn("test", keys)

        # set() should accept carrier, key, and value parameters
        carrier = {}
        setter.set(carrier, "key", "value")
        self.assertEqual(carrier, {"KEY": "value"})


if __name__ == "__main__":
    unittest.main()
