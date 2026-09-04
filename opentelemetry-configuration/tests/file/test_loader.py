# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.file import (
    ConfigurationError,
    load_config_file,
)
from opentelemetry.configuration.file._loader import (
    _SUPPORTED_SCHEMA_MAJOR,
    _SUPPORTED_SCHEMA_MINOR,
    _substitute_env_in_json_value,
    _substitute_env_in_yaml_node,
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
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
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
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
            temp_path = temp_file.name

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_config_file(temp_path)

            self.assertIn("empty", str(ctx.exception).lower())
        finally:
            os.unlink(temp_path)

    def test_non_dict_root(self):
        """Test error when root is not a mapping."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
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

        attributes = {attribute.name: attribute.value for attribute in config.resource.attributes}
        self.assertIsNone(attributes["service.name"])
        self.assertEqual(attributes["deployment.environment"], "production")

    def test_yml_extension(self):
        """Test .yml extension is supported."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as temp_file:
            temp_file.write('file_format: "1.0"')
            temp_path = temp_file.name

        try:
            config = load_config_file(temp_path)
            self.assertEqual(config.file_format, "1.0")
        finally:
            os.unlink(temp_path)

    def test_json_syntax_error(self):
        """Test error on invalid JSON syntax."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as temp_file:
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
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
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
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
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
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
            temp_file.write('file_format: "1.0"\nattribute_limits:\n  attribute_count_limit: "not-a-number"\n')
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
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
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

    def _load(self, yaml_content: str | None = None) -> OpenTelemetryConfiguration:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fh:
            fh.write(self._YAML if yaml_content is None else yaml_content)
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
        self.assertIsInstance(config.tracer_provider.processors[0], SpanProcessorConfig)
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
        self.assertIsNone(config.tracer_provider.sampler.jaeger_remote_development)
        # A sibling nullable dict-typed node (console:) was still coerced.
        self.assertEqual(config.tracer_provider.processors[0].batch.exporter.console, {})


class TestFileFormatValidation(unittest.TestCase):
    """Validate the file_format version per the configuration spec."""

    _SUPPORTED = f"{_SUPPORTED_SCHEMA_MAJOR}.{_SUPPORTED_SCHEMA_MINOR}"

    @staticmethod
    def _load(file_format: str) -> OpenTelemetryConfiguration:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fh:
            fh.write(f'file_format: "{file_format}"')
            path = fh.name
        try:
            return load_config_file(path)
        finally:
            os.unlink(path)

    def test_supported_version_is_accepted(self):
        with self.assertNoLogs("opentelemetry.configuration.file._loader", level="WARNING"):
            config = self._load(self._SUPPORTED)
        self.assertEqual(config.file_format, self._SUPPORTED)

    def test_pre_release_meta_tag_is_accepted(self):
        # The meta tag is stripped, so the version is read as the supported one.
        version = f"{self._SUPPORTED}-rc.2"
        config = self._load(version)
        self.assertEqual(config.file_format, version)

    @unittest.skipIf(
        _SUPPORTED_SCHEMA_MINOR == 0,
        "No older minor version to validate against",
    )
    def test_older_minor_is_accepted(self):
        version = f"{_SUPPORTED_SCHEMA_MAJOR}.{_SUPPORTED_SCHEMA_MINOR - 1}"
        with self.assertNoLogs("opentelemetry.configuration.file._loader", level="WARNING"):
            config = self._load(version)
        self.assertEqual(config.file_format, version)

    def test_newer_minor_is_accepted_with_warning(self):
        version = f"{_SUPPORTED_SCHEMA_MAJOR}.{_SUPPORTED_SCHEMA_MINOR + 1}"
        with self.assertLogs("opentelemetry.configuration.file._loader", level="WARNING") as logs:
            config = self._load(version)
        self.assertEqual(config.file_format, version)
        self.assertTrue(any("newer minor version" in message for message in logs.output))

    def test_unsupported_major_is_rejected(self):
        versions = ["0.4", f"{_SUPPORTED_SCHEMA_MAJOR + 1}.0"]
        for version in versions:
            with self.subTest(version=version):
                with self.assertRaises(ConfigurationError) as ctx:
                    self._load(version)
                self.assertIn("file_format", str(ctx.exception))

    def test_malformed_version_is_rejected(self):
        with self.assertRaises(ConfigurationError) as ctx:
            self._load("not-a-version")
        self.assertIn("file_format", str(ctx.exception))


def _substitute_yaml(text: str):
    """Parse ``text``, run the node walker over it, and build the document.

    This is what ``_parse_config_content`` does for YAML, without the schema
    validation, so walker behavior can be asserted on any document shape.
    """
    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
        _substitute_env_in_yaml_node(node, loader)
        return loader.construct_document(node)
    finally:
        loader.dispose()


class TestEnvVarSubstitutionScope(unittest.TestCase):
    """Substitution applies only to configuration values, per the config spec.

    These exercise the YAML node walker directly so the spec's type and
    scope rules can be asserted without the JSON schema constraining shape.
    """

    def test_unquoted_standalone_reference_is_type_coerced(self):
        with patch.dict(os.environ, {"N": "42", "FLAG": "true"}):
            result = _substitute_yaml("count: ${N}\nflag: ${FLAG}")
        self.assertEqual(result["count"], 42)
        self.assertIsInstance(result["count"], int)
        self.assertIs(result["flag"], True)

    def test_quoted_reference_stays_string(self):
        with patch.dict(os.environ, {"N": "42"}):
            result = _substitute_yaml('count: "${N}"')
        self.assertEqual(result["count"], "42")

    def test_embedded_reference_resolves_to_string(self):
        with patch.dict(os.environ, {"N": "42"}):
            result = _substitute_yaml("name: svc-${N}")
        self.assertEqual(result["name"], "svc-42")

    def test_mapping_key_is_not_substituted(self):
        # A ${VAR} in a key position is left verbatim and triggers no lookup,
        # so an undefined variable there does not raise.
        with patch.dict(os.environ, {}, clear=True):
            result = _substitute_yaml("${UNDEFINED_KEY}: value")
        self.assertEqual(result, {"${UNDEFINED_KEY}": "value"})

    def test_escape_sequence_is_not_a_reference(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _substitute_yaml("literal: $${NOT_A_VAR}")
        self.assertEqual(result["literal"], "${NOT_A_VAR}")

    def test_value_newline_cannot_inject_mapping_keys(self):
        with patch.dict(os.environ, {"VAL": "legit\nmalicious_key: injected"}):
            result = _substitute_yaml("service_name: ${VAL}")
        self.assertEqual(list(result), ["service_name"])
        self.assertEqual(result["service_name"], "legit\nmalicious_key: injected")


class TestEnvVarSubstitutionWithAliases(unittest.TestCase):
    """An anchored value is substituted once, however many aliases reach it.

    An alias resolves to the very same composed node as its anchor, so the
    walker reaches one node once per reference. Substituting it more than once
    would re-read the first pass's output and defeat the ``$$`` escape, and a
    cyclic alias would recurse without end.
    """

    def test_aliased_reference_resolves_for_every_alias(self):
        with patch.dict(os.environ, {"TOKEN": "resolved"}):
            result = _substitute_yaml("a: &anchor ${TOKEN}\nb: *anchor\nc: *anchor")
        self.assertEqual(result, {"a": "resolved", "b": "resolved", "c": "resolved"})

    def test_aliased_escape_stays_literal(self):
        # Without a visited set the first visit turns $${TOKEN} into the
        # literal ${TOKEN} and the second resolves it, leaking TOKEN's value.
        with patch.dict(os.environ, {"TOKEN": "leaked"}):
            result = _substitute_yaml("a: &anchor $${TOKEN}\nb: *anchor\nc: *anchor")
        self.assertEqual(result, {"a": "${TOKEN}", "b": "${TOKEN}", "c": "${TOKEN}"})

    def test_aliased_reference_is_type_coerced_once(self):
        with patch.dict(os.environ, {"N": "42"}):
            result = _substitute_yaml("a: &anchor ${N}\nb: *anchor")
        self.assertEqual(result["a"], 42)
        self.assertIsInstance(result["a"], int)
        self.assertEqual(result["b"], 42)

    def test_merge_key_escape_stays_literal(self):
        # A merge key's value node is the anchored mapping itself, so the
        # merged-in values are reached twice as well.
        text = "base: &base\n  x: $${TOKEN}\nderived:\n  <<: *base\n  y: 1\n"
        with patch.dict(os.environ, {"TOKEN": "leaked"}):
            result = _substitute_yaml(text)
        self.assertEqual(result, {"base": {"x": "${TOKEN}"}, "derived": {"x": "${TOKEN}", "y": 1}})

    def test_merge_key_resolves_reference(self):
        text = "base: &base\n  x: ${TOKEN}\nderived:\n  <<: *base\n  y: 1\n"
        with patch.dict(os.environ, {"TOKEN": "resolved"}):
            result = _substitute_yaml(text)
        self.assertEqual(result, {"base": {"x": "resolved"}, "derived": {"x": "resolved", "y": 1}})

    def test_cyclic_alias_terminates(self):
        # A mapping that aliases itself makes the node tree a graph with a
        # loop; the walk must end instead of raising RecursionError.
        with patch.dict(os.environ, {"TOKEN": "resolved"}):
            result = _substitute_yaml("a: &anchor\n  self: *anchor\n  value: ${TOKEN}")
        self.assertIs(result["a"]["self"], result["a"])
        self.assertEqual(result["a"]["value"], "resolved")

    def test_cyclic_alias_in_sequence_terminates(self):
        with patch.dict(os.environ, {"TOKEN": "resolved"}):
            result = _substitute_yaml("a: &anchor\n  - *anchor\n  - ${TOKEN}")
        self.assertIs(result["a"][0], result["a"])
        self.assertEqual(result["a"][1], "resolved")


class TestJsonEnvVarSubstitution(unittest.TestCase):
    """JSON substitution touches only string values, not keys or non-strings."""

    def test_string_values_substituted_keys_untouched(self):
        with patch.dict(os.environ, {"V": "resolved"}):
            result = _substitute_env_in_json_value({"${KEY}": "${V}", "nested": ["${V}", 1, True, None]})
        self.assertEqual(
            result,
            {"${KEY}": "resolved", "nested": ["resolved", 1, True, None]},
        )


class TestEnvVarSubstitutionEndToEnd(unittest.TestCase):
    """End-to-end loader behavior for issue #5406."""

    @staticmethod
    def _load_yaml(text: str) -> OpenTelemetryConfiguration:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            return load_config_file(path)
        finally:
            os.unlink(path)

    def test_undefined_variable_in_comment_does_not_crash(self):
        # The reported bug: a ${VAR} inside a comment must be ignored, so an
        # undefined variable there no longer aborts loading.
        text = "file_format: '1.0'\n# documented default uses ${UNDEFINED_VAR} - not substituted\ndisabled: false\n"
        with patch.dict(os.environ, {}, clear=True):
            config = self._load_yaml(text)
        self.assertEqual(config.file_format, "1.0")
        self.assertIs(config.disabled, False)

    def test_standalone_reference_coerces_type_for_schema(self):
        # An integer field populated from ${VAR} must be an int so it passes
        # JSON-schema validation.
        text = "file_format: '1.0'\nattribute_limits:\n  attribute_count_limit: ${LIMIT}\n"
        with patch.dict(os.environ, {"LIMIT": "100"}):
            config = self._load_yaml(text)
        self.assertEqual(config.attribute_limits.attribute_count_limit, 100)

    def test_quoted_reference_for_int_field_fails_schema(self):
        # Quoting forces a string, which is invalid for an integer field.
        text = "file_format: '1.0'\nattribute_limits:\n  attribute_count_limit: \"${LIMIT}\"\n"
        with patch.dict(os.environ, {"LIMIT": "100"}):
            with self.assertRaises(ConfigurationError) as ctx:
                self._load_yaml(text)
        self.assertIn("schema", str(ctx.exception).lower())
