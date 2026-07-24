# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from dataclasses import dataclass
from typing import Any, ClassVar

from opentelemetry.configuration._common import _additional_properties
from opentelemetry.configuration._conversion import _dict_to_dataclass
from opentelemetry.configuration.models import ExemplarFilter
from opentelemetry.configuration.models import Sampler as SamplerConfig


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
class _WithMapping:
    # ``dict[str, Any]``-typed node, like the sampler/detector leaf configs.
    option: dict[str, Any] | None = None
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

    def test_present_null_dataclass_coerced_to_empty_instance(self):
        # A present-null value on a dataclass-typed node that can be built with
        # no arguments (e.g. a metric ``console:`` exporter) becomes a
        # defaulted instance, not None. Regression test for #5451.
        result = _dict_to_dataclass({"middle": None, "name": "test"}, _Outer)
        self.assertIsInstance(result.middle, _Middle)
        self.assertIsNone(result.middle.inner)
        self.assertEqual(result.name, "test")

    def test_present_null_dataclass_with_required_field_stays_none(self):
        # ``jaeger_remote_development`` is nullable in the schema but its model
        # (ExperimentalJaegerRemoteSampler) has required fields, so it cannot
        # be defaulted. A present null must stay None rather than raising a
        # TypeError trying to instantiate it. Regression test for #5451.
        result = _dict_to_dataclass(
            {"jaeger_remote_development": None}, SamplerConfig
        )
        self.assertIsNone(result.jaeger_remote_development)

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

    def test_present_null_mapping_coerced_to_empty_dict(self):
        # A key present with a null YAML value (e.g. ``option:``) on a
        # dict-typed node means "select with empty config", so it must become
        # an empty mapping rather than None. Regression test for #5451.
        result = _dict_to_dataclass({"option": None}, _WithMapping)
        self.assertEqual(result.option, {})

    def test_explicit_empty_mapping_preserved(self):
        result = _dict_to_dataclass({"option": {}}, _WithMapping)
        self.assertEqual(result.option, {})

    def test_absent_mapping_stays_none(self):
        # An omitted optional section must remain unset, unlike a present null.
        result = _dict_to_dataclass({"name": "x"}, _WithMapping)
        self.assertIsNone(result.option)

    def test_present_null_scalar_stays_none(self):
        result = _dict_to_dataclass({"name": None}, _WithMapping)
        self.assertIsNone(result.name)
