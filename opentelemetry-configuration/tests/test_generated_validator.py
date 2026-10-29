# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Checks on the generated validator that replaces ``jsonschema`` at runtime.

``jsonschema`` stays a test dependency precisely so these can run: the point of
the generated validator is to reach the same verdicts without being installed
alongside the instrumented application, and the only way to know it does is to
ask both and compare.
"""

import json
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jsonschema

from opentelemetry.configuration import _generated_validator
from opentelemetry.configuration._validation_exceptions import (
    JsonSchemaValueException,
)

_PACKAGE_ROOT = Path(_generated_validator.__file__).parent
_SCHEMA = json.loads((_PACKAGE_ROOT / "schema.json").read_text(encoding="utf-8"))

_CODEGEN_SPEC = spec_from_file_location(
    "_generate_validator",
    Path(__file__).resolve().parent.parent / "codegen" / "_generate_validator.py",
)
_CODEGEN = module_from_spec(_CODEGEN_SPEC)
_CODEGEN_SPEC.loader.exec_module(_CODEGEN)

_VALID = {
    "file_format": "1.0-rc.1",
    "tracer_provider": {"processors": [{"simple": {"exporter": {"console": {}}}}]},
}

_DOCUMENTS = [
    ("valid", _VALID),
    ("missing file_format", {"tracer_provider": {"processors": []}}),
    (
        "missing required property",
        {"file_format": "1.0-rc.1", "tracer_provider": {"limits": {}}},
    ),
    (
        "unknown property",
        {"file_format": "1.0-rc.1", "resource": {"detectors": []}},
    ),
    (
        "value below minimum",
        {
            "file_format": "1.0-rc.1",
            "tracer_provider": {
                "processors": [{"simple": {"exporter": {"console": {}}}}],
                "limits": {"attribute_count_limit": -5},
            },
        },
    ),
    (
        "ratio above maximum",
        {
            "file_format": "1.0-rc.1",
            "tracer_provider": {
                "processors": [{"simple": {"exporter": {"console": {}}}}],
                "sampler": {"trace_id_ratio_based": {"ratio": 50}},
            },
        },
    ),
    (
        "empty array where one item is required",
        {"file_format": "1.0-rc.1", "tracer_provider": {"processors": []}},
    ),
    (
        "two exporters in one block",
        {
            "file_format": "1.0-rc.1",
            "tracer_provider": {"processors": [{"simple": {"exporter": {"console": {}, "otlp_http": {}}}}]},
        },
    ),
    ("wrong type for file_format", {"file_format": 1}),
    (
        "wrong type for a nested object",
        {"file_format": "1.0-rc.1", "tracer_provider": "console"},
    ),
]

# Keywords fastjsonschema does not implement. It ignores an unimplemented
# keyword instead of refusing the schema, which would silently under-enforce
# it, so the schema is checked for them rather than trusted.
_UNIMPLEMENTED_KEYWORDS = frozenset(
    {
        "prefixItems",
        "unevaluatedProperties",
        "unevaluatedItems",
        "dependentRequired",
        "dependentSchemas",
        "maxContains",
        "minContains",
    }
)


def _is_valid_per_jsonschema(document):
    try:
        jsonschema.validate(
            instance=document,
            schema=_SCHEMA,
            cls=jsonschema.Draft202012Validator,
        )
    except jsonschema.ValidationError:
        return False
    return True


def _is_valid_per_generated_validator(document):
    try:
        _generated_validator.validate(document)
    except JsonSchemaValueException:
        return False
    return True


def _keywords_in(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keywords_in(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keywords_in(item)


class TestGeneratedValidatorAgreesWithJsonschema(unittest.TestCase):
    def test_both_validators_reach_the_same_verdict(self):
        for label, document in _DOCUMENTS:
            with self.subTest(document=label):
                self.assertEqual(
                    _is_valid_per_generated_validator(document),
                    _is_valid_per_jsonschema(document),
                    f"the two validators disagree about {label!r}",
                )

    def test_only_the_valid_document_is_accepted(self):
        accepted = [label for label, document in _DOCUMENTS if _is_valid_per_generated_validator(document)]
        self.assertEqual(accepted, ["valid"])


class TestGeneratedValidatorCoversTheSchema(unittest.TestCase):
    def test_schema_uses_no_keyword_fastjsonschema_ignores(self):
        used = set(_keywords_in(_SCHEMA)) & _UNIMPLEMENTED_KEYWORDS
        self.assertEqual(
            used,
            set(),
            "the schema now uses keywords fastjsonschema does not implement, "
            "so the generated validator would silently accept documents "
            "jsonschema rejects",
        )


class TestGeneratedValidatorHasNoRuntimeDependency(unittest.TestCase):
    def test_it_imports_nothing_beyond_decimal_and_its_own_exceptions(self):
        source = Path(_generated_validator.__file__).read_text(encoding="utf-8")
        imported = {
            line.split()[1].split(".")[0] for line in source.splitlines() if line.startswith(("import ", "from "))
        }
        self.assertEqual(imported, {"decimal", "opentelemetry"})

    def test_a_missing_required_property_is_named_in_the_message(self):
        with self.assertRaises(JsonSchemaValueException) as caught:
            _generated_validator.validate({"tracer_provider": {}})
        self.assertIn("must contain ['file_format'] properties", str(caught.exception))


class TestGeneratedValidatorIsCurrentWithTheSchema(unittest.TestCase):
    """The committed output has to be what regenerating would produce today.

    Everything else in this module exercises the validator's behaviour, which
    says nothing about whether it was regenerated after the last change to
    ``schema.json``. A stale validator enforces the previous schema and fails
    nothing, because the only check that reads ``schema.json`` live compares
    verdicts on ten fixed documents.
    """

    def test_recompiling_the_schema_reproduces_the_committed_validator(self):
        committed = (_PACKAGE_ROOT / "_generated_validator.py").read_text(encoding="utf-8")
        recompiled = _CODEGEN.compile_validator().source
        self.assertTrue(
            recompiled == committed,
            f"schema.json no longer compiles to the committed "
            f"_generated_validator.py ({len(committed)} bytes committed, "
            f"{len(recompiled)} recompiled); run "
            f"'tox -e generate-config-validator' and commit the result",
        )

    def test_the_committed_exception_classes_match_the_pinned_fastjsonschema(self):
        committed = (_PACKAGE_ROOT / "_validation_exceptions.py").read_text(encoding="utf-8")
        self.assertTrue(
            _CODEGEN.vendored_exceptions_source() == committed,
            "_validation_exceptions.py no longer matches the exceptions module "
            "of the installed fastjsonschema; run "
            "'tox -e generate-config-validator' and commit the result",
        )
