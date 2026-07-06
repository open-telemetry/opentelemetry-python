# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from dataclasses import dataclass
from typing import Any, ClassVar

from opentelemetry.sdk._configuration._common import _additional_properties
from opentelemetry.sdk._configuration._conversion import _dict_to_dataclass
from opentelemetry.sdk._configuration.models import ExemplarFilter


@dataclass
class _Inner:
    value: int | None = None


@dataclass
class _Middle:
    inner: _Inner | None = None
    items: list[_Inner] | None = None


@dataclass
class _Outer:
    middle: _Middle | None = None
    name: str | None = None


@_additional_properties
@dataclass
class _WithExtras:
    known: str | None = None
    additional_properties: ClassVar[dict[str, Any]]


@dataclass
class _WithEnum:
    filter: ExemplarFilter | None = None


@dataclass
class _WithSlashField:
    detection_development: str | None = None
    name: str | None = None


class TestDictToDataclass(unittest.TestCase):
    def test_raises_on_non_dataclass(self):
        # _dict_to_dataclass is internal and assumes cls is a dataclass.
        with self.assertRaises(TypeError) as ctx:
            _dict_to_dataclass({"x": 1}, dict)
        self.assertIn("not a dataclass", str(ctx.exception))

    def test_converts_flat_dict(self):
        result = _dict_to_dataclass({"value": 42}, _Inner)
        self.assertIsInstance(result, _Inner)
        self.assertEqual(result.value, 42)

    def test_converts_nested_dataclass(self):
        result = _dict_to_dataclass(
            {"middle": {"inner": {"value": 7}}}, _Outer
        )
        self.assertIsInstance(result, _Outer)
        self.assertIsInstance(result.middle, _Middle)
        self.assertIsInstance(result.middle.inner, _Inner)
        self.assertEqual(result.middle.inner.value, 7)

    def test_converts_list_of_dataclasses(self):
        result = _dict_to_dataclass(
            {"middle": {"items": [{"value": 1}, {"value": 2}]}}, _Outer
        )
        self.assertEqual(len(result.middle.items), 2)
        self.assertIsInstance(result.middle.items[0], _Inner)
        self.assertEqual(result.middle.items[0].value, 1)
        self.assertEqual(result.middle.items[1].value, 2)

    def test_none_value_preserved(self):
        result = _dict_to_dataclass({"middle": None, "name": "test"}, _Outer)
        self.assertIsNone(result.middle)
        self.assertEqual(result.name, "test")

    def test_missing_optional_fields_default_to_none(self):
        result = _dict_to_dataclass({}, _Outer)
        self.assertIsNone(result.middle)
        self.assertIsNone(result.name)

    def test_unknown_keys_routed_to_additional_properties(self):
        result = _dict_to_dataclass(
            {"known": "yes", "my_plugin": {"opt": True}}, _WithExtras
        )
        self.assertEqual(result.known, "yes")
        self.assertEqual(
            result.additional_properties, {"my_plugin": {"opt": True}}
        )

    def test_primitive_values_pass_through(self):
        result = _dict_to_dataclass({"name": "hello"}, _Outer)
        self.assertEqual(result.name, "hello")

    def test_empty_list_converted(self):
        result = _dict_to_dataclass({"middle": {"items": []}}, _Outer)
        self.assertEqual(result.middle.items, [])

    def test_enum_value_coerced_from_string(self):
        result = _dict_to_dataclass({"filter": "always_on"}, _WithEnum)
        self.assertIs(result.filter, ExemplarFilter.always_on)

    def test_enum_value_already_enum_passes_through(self):
        result = _dict_to_dataclass(
            {"filter": ExemplarFilter.trace_based}, _WithEnum
        )
        self.assertIs(result.filter, ExemplarFilter.trace_based)

    def test_slash_key_mapped_to_underscore_field(self):
        result = _dict_to_dataclass(
            {"name": "hello", "detection/development": "some_value"},
            _WithSlashField,
        )
        self.assertEqual(result.name, "hello")
        self.assertEqual(result.detection_development, "some_value")

    def test_slash_key_normalized_in_additional_properties(self):
        result = _dict_to_dataclass(
            {"known": "yes", "detection/development": "value"}, _WithExtras
        )
        self.assertEqual(result.known, "yes")
        self.assertEqual(
            result.additional_properties, {"detection_development": "value"}
        )
