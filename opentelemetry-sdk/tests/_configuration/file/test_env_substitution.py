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

from opentelemetry.sdk._configuration.file import (
    EnvSubstitutionError,
    substitute_env_vars,
)


class TestEnvSubstitution(unittest.TestCase):
    """Test environment variable substitution."""

    def test_simple_substitution(self):
        """Test basic ${VAR} substitution."""
        with patch.dict(os.environ, {"SERVICE_NAME": "my-service"}):
            result = substitute_env_vars("name: ${SERVICE_NAME}")
            self.assertEqual(result, "name: my-service")

    def test_multiple_substitutions(self):
        """Test multiple ${VAR} in same string."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080"}):
            result = substitute_env_vars("url: http://${HOST}:${PORT}")
            self.assertEqual(result, "url: http://localhost:8080")

    def test_substitution_with_default(self):
        """Test ${VAR:-default} with missing variable."""
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("name: ${SERVICE_NAME:-default}")
            self.assertEqual(result, "name: default")

    def test_substitution_with_default_override(self):
        """Test ${VAR:-default} with present variable."""
        with patch.dict(os.environ, {"SERVICE_NAME": "actual"}):
            result = substitute_env_vars("name: ${SERVICE_NAME:-default}")
            self.assertEqual(result, "name: actual")

    def test_missing_variable_raises_error(self):
        """Test ${VAR} raises error when variable missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EnvSubstitutionError) as ctx:
                substitute_env_vars("name: ${MISSING_VAR}")
            self.assertIn("MISSING_VAR", str(ctx.exception))

    def test_dollar_sign_escape(self):
        """Test $$ escapes to literal $."""
        result = substitute_env_vars("price: $$100")
        self.assertEqual(result, "price: $100")

    def test_dollar_sign_escape_with_substitution(self):
        """Test $$ with ${VAR} in same string."""
        with patch.dict(os.environ, {"AMOUNT": "50"}):
            result = substitute_env_vars("price: $$${AMOUNT}")
            self.assertEqual(result, "price: $50")

    def test_empty_default(self):
        """Test ${VAR:-} with empty default value."""
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("name: ${VAR:-}")
            self.assertEqual(result, "name: ")

    def test_default_with_special_chars(self):
        """Test default value containing special characters."""
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("url: ${URL:-http://localhost:8080}")
            self.assertEqual(result, "url: http://localhost:8080")

    def test_no_substitution_needed(self):
        """Test string without any variables."""
        result = substitute_env_vars("plain text without variables")
        self.assertEqual(result, "plain text without variables")

    def test_variable_name_with_underscores(self):
        """Test variable names with underscores."""
        with patch.dict(os.environ, {"MY_VAR_NAME": "value"}):
            result = substitute_env_vars("key: ${MY_VAR_NAME}")
            self.assertEqual(result, "key: value")

    def test_variable_name_with_numbers(self):
        """Test variable names with numbers."""
        with patch.dict(os.environ, {"VAR_123": "value"}):
            result = substitute_env_vars("key: ${VAR_123}")
            self.assertEqual(result, "key: value")

    def test_multiline_substitution(self):
        """Test substitution across multiple lines."""
        with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}):
            text = """line1: ${VAR1}
line2: ${VAR2}"""
            result = substitute_env_vars(text)
            expected = """line1: value1
line2: value2"""
            self.assertEqual(result, expected)

    def test_empty_string(self):
        """Test empty string returns empty string."""
        result = substitute_env_vars("")
        self.assertEqual(result, "")

    def test_only_dollar_signs(self):
        """Test string with only escaped dollar signs."""
        result = substitute_env_vars("$$$$")
        self.assertEqual(result, "$$")
