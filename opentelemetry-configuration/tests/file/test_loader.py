# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.file import (
    ConfigurationError,
    load_config_file,
)
from opentelemetry.configuration.models import (
    BatchSpanProcessor as BatchSpanProcessorConfig,
)
from opentelemetry.configuration.models import OpenTelemetryConfiguration
from opentelemetry.configuration.models import (
    ParentBasedSampler as ParentBasedSamplerConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased


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
        self.assertEqual(config.file_format, "1.0")

    def test_load_minimal_json(self):
        """Test loading minimal JSON configuration."""
        config_path = self.test_data_dir / "minimal_config.json"
        config = load_config_file(str(config_path))

        self.assertIsInstance(config, OpenTelemetryConfiguration)
        self.assertEqual(config.file_format, "1.0")

    def test_load_config_with_env_vars(self):
        """Test loading configuration with environment variable substitution."""
        config_path = self.test_data_dir / "config_with_env_vars.yaml"

        with patch.dict(os.environ, {"SERVICE_NAME": "test-service"}):
            config = load_config_file(str(config_path))

            self.assertIsInstance(config, OpenTelemetryConfiguration)

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
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as temp_file:
            temp_file.write(b"file_format: 1.0")
            temp_path = temp_file.name

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
        ) as temp_file:
            temp_path = temp_file.name

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
        ) as temp_file:
            temp_file.write("- item1\n- item2")
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("mapping", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_unset_env_var_without_default_substitutes_empty(self):
        """An unset env var without a default resolves to an empty value.

        Per the declarative configuration spec, an unset ``${VAR}`` reference
        with no default is replaced with an empty value rather than raising,
        so the file still loads. A default (``${ENV:-production}``) is still
        applied when its variable is unset.
        """
        config_path = self.test_data_dir / "config_with_env_vars.yaml"

        with patch.dict(os.environ, {}, clear=True):
            config = load_config_file(str(config_path))

        attributes = {
            attribute.name: attribute.value
            for attribute in config.resource.attributes
        }
        self.assertIsNone(attributes["service.name"])
        self.assertEqual(attributes["deployment.environment"], "production")

    def test_yml_extension(self):
        """Test .yml extension is supported."""
        with tempfile.NamedTemporaryFile(
            suffix=".yml", delete=False, mode="w"
        ) as temp_file:
            temp_file.write('file_format: "1.0"')
            temp_path = temp_file.name

        try:
            config = load_config_file(temp_path)
            self.assertEqual(config.file_format, "1.0")
        finally:
            os.unlink(temp_path)

    def test_json_syntax_error(self):
        """Test error on invalid JSON syntax."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as temp_file:
            temp_file.write('{"file_format": invalid}')
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("json", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_schema_validation_wrong_type(self):
        """Test error when field has wrong type."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as temp_file:
            # disabled must be a boolean, not a string
            temp_file.write('file_format: "1.0"\ndisabled: "yes"')
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("schema", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_schema_validation_missing_file_format(self):
        """Test error when required file_format field is missing."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as temp_file:
            temp_file.write("disabled: false")
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("schema", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_schema_validation_nested_path_in_error(self):
        """Test that error message includes field path for nested violations."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as temp_file:
            temp_file.write(
                'file_format: "1.0"\n'
                "attribute_limits:\n"
                '  attribute_count_limit: "not-a-number"\n'
            )
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            error = str(ctx.exception)
            self.assertIn("schema", error.lower())
            self.assertIn("attribute_limits", error)
            self.assertIn("attribute_count_limit", error)
        finally:
            os.unlink(temp_path)

    def test_schema_validation_invalid_enum(self):
        """Test error when field value is not a valid enum value."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as temp_file:
            temp_file.write('file_format: "1.0"\nlog_level: INVALID_LEVEL')
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("schema", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)


class TestConfigLoaderEndToEnd(unittest.TestCase):
    """Smoke-test the full YAML -> typed config -> SDK object pipeline.

    Unit tests in test_conversion.py exercise the dict-to-dataclass
    conversion in isolation; these tests verify it composes with the
    real loader and downstream factory functions on a representative
    nested configuration.
    """

    _YAML = """
file_format: '1.0'
tracer_provider:
  processors:
    - batch:
        exporter:
          console: {}
  sampler:
    parent_based:
      root:
        trace_id_ratio_based: {ratio: 0.5}
"""

    def _load(self, yaml: str | None = None) -> OpenTelemetryConfiguration:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as fh:
            fh.write(self._YAML if yaml is None else yaml)
            path = fh.name
        try:
            return load_config_file(path)
        finally:
            os.unlink(path)

    def test_nested_fields_are_typed_dataclasses(self):
        config = self._load()

        self.assertIsInstance(config.tracer_provider, TracerProviderConfig)
        self.assertIsInstance(
            config.tracer_provider.sampler.parent_based,
            ParentBasedSamplerConfig,
        )
        # Lists of dataclasses are converted element-wise.
        self.assertIsInstance(
            config.tracer_provider.processors[0], SpanProcessorConfig
        )
        self.assertIsInstance(
            config.tracer_provider.processors[0].batch,
            BatchSpanProcessorConfig,
        )

    # pylint: disable=protected-access
    def test_typed_config_feeds_factory_function(self):
        config = self._load()

        provider = create_tracer_provider(config.tracer_provider)

        self.assertIsInstance(provider, SdkTracerProvider)
        # Sampler wiring from the YAML: parent_based(trace_id_ratio_based(0.5)).
        self.assertIsInstance(provider.sampler, ParentBased)
        self.assertIsInstance(provider.sampler._root, TraceIdRatioBased)
        self.assertEqual(provider.sampler._root.rate, 0.5)
        # Span processor wiring from the YAML: batch(console).
        processors = provider._active_span_processor._span_processors
        self.assertEqual(len(processors), 1)
        self.assertIsInstance(processors[0], BatchSpanProcessor)
        self.assertIsInstance(processors[0].span_exporter, ConsoleSpanExporter)

    def test_null_valued_required_field_node_survives_conversion(self):
        # Regression test for #5451: ``jaeger_remote_development`` is nullable
        # in the schema (so ``jaeger_remote_development:`` passes validation and
        # is NOT rejected before conversion), yet its model has required
        # fields. Coercing the present null into it would raise TypeError, so
        # it must be left as None instead. The rest of the config still loads.
        config = self._load(
            """
file_format: '1.0'
tracer_provider:
  processors:
    - batch:
        exporter:
          console:
  sampler:
    jaeger_remote_development:
"""
        )

        # Schema accepted the null, and conversion left the required-field
        # node unset rather than crashing.
        self.assertIsNone(
            config.tracer_provider.sampler.jaeger_remote_development
        )
        # A sibling nullable dict-typed node (console:) was still coerced.
        self.assertEqual(
            config.tracer_provider.processors[0].batch.exporter.console, {}
        )


class TestFileFormatValidation(unittest.TestCase):
    """Validate the file_format version per the configuration spec."""

    @staticmethod
    def _load(file_format: str) -> OpenTelemetryConfiguration:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as fh:
            fh.write(f'file_format: "{file_format}"')
            path = fh.name
        try:
            return load_config_file(path)
        finally:
            os.unlink(path)

    def test_supported_version_is_accepted(self):
        config = self._load("1.0")
        self.assertEqual(config.file_format, "1.0")

    def test_pre_release_meta_tag_is_accepted(self):
        # The meta tag is stripped; "1.0-rc.2" is treated as 1.0.
        config = self._load("1.0-rc.2")
        self.assertEqual(config.file_format, "1.0-rc.2")

    def test_newer_minor_is_accepted_with_warning(self):
        with self.assertLogs(
            "opentelemetry.configuration.file._loader", level="WARNING"
        ) as logs:
            config = self._load("1.1")
        self.assertEqual(config.file_format, "1.1")
        self.assertTrue(
            any("newer minor version" in message for message in logs.output)
        )

    def test_unsupported_major_is_rejected(self):
        for version in ("2.0", "0.4"):
            with self.subTest(version=version):
                with self.assertRaises(ConfigurationError) as ctx:
                    self._load(version)
                self.assertIn("file_format", str(ctx.exception))

    def test_malformed_version_is_rejected(self):
        with self.assertRaises(ConfigurationError) as ctx:
            self._load("not-a-version")
        self.assertIn("file_format", str(ctx.exception))
