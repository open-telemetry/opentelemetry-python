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
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opentelemetry.sdk._configuration.file import (
    ConfigurationError,
    load_config_file,
)
from opentelemetry.sdk._configuration.models import OpenTelemetryConfiguration


class TestConfigLoader(unittest.TestCase):
    """Test configuration file loading."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = Path(__file__).parent / "data"

    def test_load_minimal_yaml(self):
        """Test loading minimal YAML configuration."""
        config_path = self.test_data_dir / "minimal_config.yaml"
        config = load_config_file(str(config_path))

        self.assertIsInstance(config, OpenTelemetryConfiguration)
        self.assertEqual(config.file_format, "1.0-rc.3")

    def test_load_minimal_json(self):
        """Test loading minimal JSON configuration."""
        config_path = self.test_data_dir / "minimal_config.json"
        config = load_config_file(str(config_path))

        self.assertIsInstance(config, OpenTelemetryConfiguration)
        self.assertEqual(config.file_format, "1.0-rc.3")

    def test_load_config_with_env_vars(self):
        """Test loading configuration with environment variable substitution."""
        config_path = self.test_data_dir / "config_with_env_vars.yaml"

        with patch.dict(os.environ, {"SERVICE_NAME": "test-service"}):
            config = load_config_file(str(config_path))

            self.assertIsInstance(config, OpenTelemetryConfiguration)
            # Note: Full validation of nested structures will be in later PRs
            # For now, just verify it loads without error

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with self.assertRaises(ConfigurationError) as ctx:
            load_config_file("nonexistent_file.yaml")

        self.assertIn("not found", str(ctx.exception))

    def test_directory_instead_of_file(self):
        """Test error when path is a directory."""
        with self.assertRaises(ConfigurationError) as ctx:
            load_config_file(str(self.test_data_dir))

        self.assertIn("not a file", str(ctx.exception))

    def test_invalid_yaml_syntax(self):
        """Test error on invalid YAML syntax."""
        config_path = self.test_data_dir / "invalid_yaml.yaml"

        with self.assertRaises(ConfigurationError) as ctx:
            load_config_file(str(config_path))

        self.assertIn("yaml", str(ctx.exception).lower())

    def test_invalid_file_extension(self):
        """Test error on unsupported file extension."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"file_format: 1.0-rc.3")
            temp_path = f.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("Unsupported file format", str(ctx.exception))
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Test error on empty file."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as f:
            temp_path = f.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("empty", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_non_dict_root(self):
        """Test error when root is not a mapping."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as f:
            f.write("- item1\n- item2")
            temp_path = f.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("mapping", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_missing_required_env_var(self):
        """Test error when required env var is missing."""
        config_path = self.test_data_dir / "config_with_env_vars.yaml"

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(str(config_path))

            # Should mention substitution or env var error
            self.assertTrue(
                "substitution" in str(ctx.exception).lower()
                or "environment" in str(ctx.exception).lower()
            )

    def test_yml_extension(self):
        """Test .yml extension is supported."""
        with tempfile.NamedTemporaryFile(
            suffix=".yml", delete=False, mode="w"
        ) as f:
            f.write('file_format: "1.0-rc.3"')
            temp_path = f.name

        try:
            config = load_config_file(temp_path)
            self.assertEqual(config.file_format, "1.0-rc.3")
        finally:
            os.unlink(temp_path)

    def test_json_syntax_error(self):
        """Test error on invalid JSON syntax."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            f.write('{"file_format": invalid}')
            temp_path = f.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("json", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)
