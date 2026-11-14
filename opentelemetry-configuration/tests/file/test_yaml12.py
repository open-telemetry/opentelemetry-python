# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""YAML 1.2 Core Schema behavior for declarative configuration files.

The configuration spec requires YAML 1.2 parsed with the Core schema
(https://yaml.org/spec/1.2.2/#103-core-schema). PyYAML's SafeLoader implements
YAML 1.1, so these tests pin the scalars that must change and the env-var
substitution rules that re-resolve a plain ``${VAR}`` after replacement.
"""

import math
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from opentelemetry.configuration.file import (
    ConfigurationError,
    load_config_file,
)
from opentelemetry.configuration.file._loader import _parse_config_content


def _parse(text: str):
    return _parse_config_content(text, ".yaml", "config.yaml")


class TestYAML12CoreSchemaScalars(unittest.TestCase):
    """Plain scalars follow the YAML 1.2 Core schema, not PyYAML's YAML 1.1."""

    def test_yaml11_bool_words_stay_strings(self):
        # YAML 1.1 treats these as booleans. Core schema does not.
        for literal in (
            "on",
            "off",
            "On",
            "Off",
            "ON",
            "OFF",
            "yes",
            "no",
            "Yes",
            "No",
            "YES",
            "NO",
            "y",
            "n",
            "Y",
            "N",
        ):
            with self.subTest(literal=literal):
                self.assertEqual(_parse(f"key: {literal}\n")["key"], literal)

    def test_yaml11_bool_words_used_as_keys_stay_strings(self):
        result = _parse("on: enabled\nyes: enabled\n")
        self.assertEqual(result, {"on": "enabled", "yes": "enabled"})

    def test_core_schema_booleans(self):
        for literal, expected in (
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
        ):
            with self.subTest(literal=literal):
                self.assertIs(_parse(f"key: {literal}\n")["key"], expected)

    def test_core_schema_nulls(self):
        for literal in ("null", "Null", "NULL", "~"):
            with self.subTest(literal=literal):
                self.assertIsNone(_parse(f"key: {literal}\n")["key"])
        # An empty plain scalar is null. A quoted empty scalar is a string.
        self.assertIsNone(_parse("key:\n")["key"])
        self.assertEqual(_parse('key: ""\n')["key"], "")
        self.assertEqual(_parse("key: ''\n")["key"], "")

    def test_sexagesimal_and_other_yaml11_numbers_stay_strings(self):
        for literal in (
            "1:20",
            "1:20:30",
            "190:20:30.15",
            "0b10",
            "0b1010",
            "1_000",
            "1_000.5",
            "0x_ff",
            "+0x10",
            "-0o7",
            "0O10",
            "0X10",
            "0o",
            "0x",
        ):
            with self.subTest(literal=literal):
                self.assertEqual(_parse(f"key: {literal}\n")["key"], literal)

    def test_legacy_octal_is_decimal_and_0o_0x_are_ints(self):
        cases = (
            ("010", 10),
            ("00", 0),
            ("08", 8),
            ("09", 9),
            ("+010", 10),
            ("-010", -10),
            ("0o10", 8),
            ("0o755", 493),
            ("0o0", 0),
            ("0x10", 16),
            ("0xdeadbeef", 3735928559),
            ("0xDEADBEEF", 3735928559),
            ("42", 42),
            ("+42", 42),
            ("-17", -17),
            ("-0", 0),
        )
        for literal, expected in cases:
            with self.subTest(literal=literal):
                value = _parse(f"key: {literal}\n")["key"]
                self.assertEqual(value, expected)
                self.assertIsInstance(value, int)
                self.assertNotIsInstance(value, bool)

    def test_core_schema_floats(self):
        cases = (
            ("1.5", 1.5),
            (".5", 0.5),
            ("5.", 5.0),
            ("1e2", 100.0),
            ("1E+2", 100.0),
            ("1.5e-2", 0.015),
            ("1.1", 1.1),
            ("+.inf", math.inf),
            ("-.inf", -math.inf),
            (".Inf", math.inf),
            (".INF", math.inf),
            ("-.INF", -math.inf),
        )
        for literal, expected in cases:
            with self.subTest(literal=literal):
                value = _parse(f"key: {literal}\n")["key"]
                self.assertEqual(value, expected)
                self.assertIsInstance(value, float)

    def test_core_schema_nan(self):
        for literal in (".nan", ".NaN", ".NAN"):
            with self.subTest(literal=literal):
                value = _parse(f"key: {literal}\n")["key"]
                self.assertIsInstance(value, float)
                self.assertTrue(math.isnan(value))
        # A sign is not part of the Core schema NaN production.
        for literal in ("+.nan", "-.nan", "nan", ".infinity", "inf"):
            with self.subTest(literal=literal):
                self.assertEqual(_parse(f"key: {literal}\n")["key"], literal)

    def test_timestamps_value_tag_and_merge_are_not_core_schema_types(self):
        self.assertEqual(_parse("key: 2024-01-02\n")["key"], "2024-01-02")
        self.assertEqual(
            _parse("key: 2024-01-02T03:04:05Z\n")["key"],
            "2024-01-02T03:04:05Z",
        )
        # YAML 1.1's value tag (`=`) has no Core schema constructor.
        self.assertEqual(_parse("key: =\n")["key"], "=")
        # `<<` is an ordinary key. It does not merge the anchored mapping.
        merged = _parse("base: &base\n  x: 1\nderived:\n  <<: *base\n  y: 2\n")
        self.assertEqual(merged, {"base": {"x": 1}, "derived": {"<<": {"x": 1}, "y": 2}})

    def test_explicit_yaml11_tags_are_rejected(self):
        for text in (
            "key: !!timestamp 2024-01-02\n",
            'key: !!binary "YQ=="\n',
            "key: !!bool yes\n",
            "key: !!bool YES\n",
            "key: !!bool on\n",
            "key: !!bool off\n",
            "key: !!bool y\n",
            "key: !!bool n\n",
            "key: !!bool maybe\n",
            "key: !!int 1_000\n",
            "key: !!int +0x10\n",
            "key: !!int -0o7\n",
            "key: !!int 0b10\n",
            "key: !!int 1:20\n",
            "key: !!float 1_000\n",
            "key: !!float 1_000.5\n",
            "key: !!float +.nan\n",
            "key: !!float -.nan\n",
            "key: !!float 1:20\n",
        ):
            with self.subTest(text=text):
                with self.assertRaises(ConfigurationError):
                    _parse(text)

    def test_explicit_core_tags_accept_valid_forms(self):
        self.assertIs(_parse("key: !!bool true\n")["key"], True)
        self.assertIs(_parse("key: !!bool FALSE\n")["key"], False)
        self.assertEqual(_parse("key: !!int 010\n")["key"], 10)
        self.assertEqual(_parse("key: !!int 0o10\n")["key"], 8)
        self.assertEqual(_parse("key: !!int 0x10\n")["key"], 16)
        self.assertEqual(_parse("key: !!float 10.\n")["key"], 10.0)
        self.assertEqual(_parse("key: !!float +.inf\n")["key"], math.inf)
        self.assertTrue(math.isnan(_parse("key: !!float .nan\n")["key"]))
        self.assertEqual(_parse("key: !!str on\n")["key"], "on")

    def test_quoted_scalars_stay_strings(self):
        for literal in ('"on"', '"true"', '"010"', '"1:20"', '"0o10"', "'yes'", "'null'"):
            with self.subTest(literal=literal):
                value = _parse(f"key: {literal}\n")["key"]
                self.assertIsInstance(value, str)
                self.assertNotIn(value[0], "\"'")

    def test_nested_scalars_use_core_schema(self):
        text = "seq:\n  - on\n  - 1:20\n  - 010\n  - true\n  - 0o10\nmap:\n  yes: off\n"
        self.assertEqual(
            _parse(text),
            {
                "seq": ["on", "1:20", 10, True, 8],
                "map": {"yes": "off"},
            },
        )

    def test_parsing_does_not_mutate_pyyaml_safe_loader(self):
        bases = [yaml.loader.SafeLoader]
        if yaml.SafeLoader is not yaml.loader.SafeLoader:
            bases.append(yaml.SafeLoader)
        snapshots = []
        for base in bases:
            snapshots.append(
                (
                    base,
                    id(base.yaml_implicit_resolvers),
                    {key: id(resolvers) for key, resolvers in base.yaml_implicit_resolvers.items()},
                    {
                        key: [(tag, regex.pattern) for tag, regex in resolvers]
                        for key, resolvers in base.yaml_implicit_resolvers.items()
                    },
                )
            )

        self.assertEqual(_parse("flag: on\ncount: 1:20\noctal: 010\n"), {"flag": "on", "count": "1:20", "octal": 10})

        for base, resolver_id, list_ids, patterns in snapshots:
            self.assertEqual(id(base.yaml_implicit_resolvers), resolver_id)
            self.assertEqual(
                {key: id(resolvers) for key, resolvers in base.yaml_implicit_resolvers.items()},
                list_ids,
            )
            self.assertEqual(
                {
                    key: [(tag, regex.pattern) for tag, regex in resolvers]
                    for key, resolvers in base.yaml_implicit_resolvers.items()
                },
                patterns,
            )
        # Callers of PyYAML itself still get YAML 1.1 from the untouched loader.
        self.assertIs(yaml.safe_load("flag: on")["flag"], True)
        self.assertEqual(yaml.safe_load("count: 1:20")["count"], 80)
        self.assertEqual(yaml.safe_load("octal: 010")["octal"], 8)


class TestYAML12EnvSubstitution(unittest.TestCase):
    """A plain ``${VAR}`` is re-resolved with Core schema rules after substitution."""

    def test_standalone_reference_uses_core_schema(self):
        cases = {
            "on": "on",
            "off": "off",
            "yes": "yes",
            "no": "no",
            "y": "y",
            "n": "n",
            "On": "On",
            "YES": "YES",
            "true": True,
            "True": True,
            "TRUE": True,
            "false": False,
            "FALSE": False,
            "123": 123,
            "010": 10,
            "08": 8,
            "0o10": 8,
            "0x10": 16,
            "0xdeadbeef": 3735928559,
            "1.5": 1.5,
            "1.1": 1.1,
            "1e2": 100.0,
            "1:20": "1:20",
            "1:20:30": "1:20:30",
            "0b10": "0b10",
            "1_000": "1_000",
            "+0x10": "+0x10",
            "2024-01-02": "2024-01-02",
            "null": None,
            "~": None,
            "=": "=",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                with patch.dict(os.environ, {"VAL": raw}):
                    value = _parse("key: ${VAL}\n")["key"]
                if isinstance(expected, float):
                    self.assertEqual(value, expected)
                    self.assertIsInstance(value, float)
                elif isinstance(expected, bool):
                    self.assertIs(value, expected)
                else:
                    self.assertEqual(value, expected)
                    if isinstance(expected, int):
                        self.assertIsInstance(value, int)
                        self.assertNotIsInstance(value, bool)

    def test_inf_and_nan_from_env(self):
        with patch.dict(os.environ, {"POS": ".inf", "NEG": "-.INF", "NAN": ".nan", "SIGNED": "+.nan"}):
            result = _parse("pos: ${POS}\nneg: ${NEG}\nnan: ${NAN}\nsigned: ${SIGNED}\n")
        self.assertTrue(math.isinf(result["pos"]) and result["pos"] > 0)
        self.assertTrue(math.isinf(result["neg"]) and result["neg"] < 0)
        self.assertTrue(math.isnan(result["nan"]))
        self.assertEqual(result["signed"], "+.nan")

    def test_quoted_reference_stays_string(self):
        for raw in ("on", "true", "123", "010", "1:20", "null", ".inf"):
            with self.subTest(raw=raw):
                with patch.dict(os.environ, {"VAL": raw}):
                    double = _parse('key: "${VAL}"\n')["key"]
                    single = _parse("key: '${VAL}'\n")["key"]
                self.assertEqual(double, raw)
                self.assertEqual(single, raw)
                self.assertIsInstance(double, str)

    def test_embedded_reference_stays_string(self):
        with patch.dict(os.environ, {"VAL": "on"}):
            self.assertEqual(_parse("key: x${VAL}\n")["key"], "xon")

    def test_default_value_is_re_resolved(self):
        cases = {
            "${UNSET:-on}": "on",
            "${UNSET:-true}": True,
            "${UNSET:-123}": 123,
            "${UNSET:-010}": 10,
            "${UNSET:-0o10}": 8,
            "${UNSET:-1:20}": "1:20",
            "${UNSET:-yes}": "yes",
            "${env:UNSET:-false}": False,
        }
        with patch.dict(os.environ, {}, clear=True):
            for reference, expected in cases.items():
                with self.subTest(reference=reference):
                    value = _parse(f"key: {reference}\n")["key"]
                    if isinstance(expected, bool):
                        self.assertIs(value, expected)
                    else:
                        self.assertEqual(value, expected)

    def test_env_prefix_is_re_resolved(self):
        with patch.dict(os.environ, {"VAL": "on", "N": "010"}):
            result = _parse("flag: ${env:VAL}\ncount: ${env:N}\n")
        self.assertEqual(result["flag"], "on")
        self.assertEqual(result["count"], 10)
        self.assertIsInstance(result["count"], int)

    def test_unset_standalone_reference_is_null(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_parse("key: ${UNSET}\n")["key"])


class TestYAML12LoadConfigFile(unittest.TestCase):
    """Issue #5909: load_config_file applies Core schema before schema validation."""

    def _load(self, text: str):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as handle:
            handle.write(text)
            path = handle.name
        self.addCleanup(os.unlink, path)
        return load_config_file(path)

    def test_resource_attribute_yaml11_literals_stay_strings(self):
        text = (
            'file_format: "1.0"\n'
            "resource:\n"
            "  attributes:\n"
            "    - name: flag\n"
            "      value: on\n"
            "    - name: answer\n"
            "      value: yes\n"
            "    - name: ratio\n"
            "      value: 1:20\n"
            "    - name: when\n"
            "      value: 2024-01-02\n"
        )
        config = self._load(text)
        values = [attribute.value for attribute in config.resource.attributes]
        self.assertEqual(values, ["on", "yes", "1:20", "2024-01-02"])

    def test_legacy_octal_integer_field_is_decimal(self):
        text = "file_format: '1.0'\nattribute_limits:\n  attribute_count_limit: 010\n"
        config = self._load(text)
        self.assertEqual(config.attribute_limits.attribute_count_limit, 10)

    def test_explicit_octal_integer_field(self):
        text = "file_format: '1.0'\nattribute_limits:\n  attribute_count_limit: 0o12\n"
        config = self._load(text)
        self.assertEqual(config.attribute_limits.attribute_count_limit, 10)

    def test_env_integer_field_legacy_octal_is_decimal(self):
        text = "file_format: '1.0'\nattribute_limits:\n  attribute_count_limit: ${LIMIT}\n"
        with patch.dict(os.environ, {"LIMIT": "010"}):
            config = self._load(text)
        self.assertEqual(config.attribute_limits.attribute_count_limit, 10)

    def test_env_bool_true_still_coerces(self):
        text = "file_format: '1.0'\ndisabled: ${FLAG}\n"
        with patch.dict(os.environ, {"FLAG": "true"}):
            config = self._load(text)
        self.assertIs(config.disabled, True)

    def test_env_bool_word_on_fails_schema_as_string(self):
        text = "file_format: '1.0'\ndisabled: ${FLAG}\n"
        with patch.dict(os.environ, {"FLAG": "on"}):
            with self.assertRaises(ConfigurationError) as ctx:
                self._load(text)
        self.assertIn("schema", str(ctx.exception).lower())

    def test_plain_on_is_not_a_boolean_field(self):
        text = "file_format: '1.0'\ndisabled: on\n"
        with self.assertRaises(ConfigurationError) as ctx:
            self._load(text)
        self.assertIn("schema", str(ctx.exception).lower())
