# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

import opentelemetry.configuration._config_provider as config_provider_module
from opentelemetry.configuration._config_provider import (
    ConfigProperties,
    ConfigProvider,
    _node_to_mapping,
    get_config_provider,
    set_config_provider,
)
from opentelemetry.configuration.models import (
    ExperimentalGeneralInstrumentation,
    ExperimentalInstrumentation,
)


class TestConfigPropertiesScalars(unittest.TestCase):
    def setUp(self):
        self.props = ConfigProperties(
            {
                "name": "service",
                "flag": True,
                "count": 5,
                "ratio": 0.25,
                "whole": 3,
            }
        )

    def test_get_string(self):
        self.assertEqual(self.props.get_string("name"), "service")

    def test_get_string_missing_returns_none(self):
        self.assertIsNone(self.props.get_string("nope"))

    def test_get_string_wrong_type_returns_none(self):
        self.assertIsNone(self.props.get_string("count"))

    def test_get_bool(self):
        self.assertIs(self.props.get_bool("flag"), True)

    def test_get_bool_wrong_type_returns_none(self):
        self.assertIsNone(self.props.get_bool("count"))

    def test_get_int(self):
        self.assertEqual(self.props.get_int("count"), 5)

    def test_get_int_rejects_bool(self):
        self.assertIsNone(self.props.get_int("flag"))

    def test_get_int_wrong_type_returns_none(self):
        self.assertIsNone(self.props.get_int("name"))

    def test_get_float(self):
        self.assertEqual(self.props.get_float("ratio"), 0.25)

    def test_get_float_widens_int(self):
        result = self.props.get_float("whole")
        self.assertIsInstance(result, float)
        self.assertEqual(result, 3.0)

    def test_get_float_rejects_bool(self):
        self.assertIsNone(self.props.get_float("flag"))

    def test_keys(self):
        self.assertEqual(
            set(self.props.keys()),
            {"name", "flag", "count", "ratio", "whole"},
        )

    def test_contains(self):
        self.assertIn("name", self.props)
        self.assertNotIn("nope", self.props)


class TestConfigPropertiesStructured(unittest.TestCase):
    def test_get_config_returns_sub_view(self):
        props = ConfigProperties({"peer": {"host": "localhost", "port": 8080}})
        sub = props.get_config("peer")
        self.assertIsInstance(sub, ConfigProperties)
        self.assertEqual(sub.get_string("host"), "localhost")
        self.assertEqual(sub.get_int("port"), 8080)

    def test_get_config_missing_returns_none(self):
        self.assertIsNone(ConfigProperties({}).get_config("peer"))

    def test_get_config_non_mapping_returns_none(self):
        self.assertIsNone(ConfigProperties({"peer": 5}).get_config("peer"))

    def test_get_config_list(self):
        props = ConfigProperties({"servers": [{"host": "a"}, {"host": "b"}]})
        result = props.get_config_list("servers")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].get_string("host"), "a")
        self.assertEqual(result[1].get_string("host"), "b")

    def test_get_config_list_missing_returns_none(self):
        self.assertIsNone(ConfigProperties({}).get_config_list("servers"))

    def test_get_scalar_list_strings(self):
        props = ConfigProperties({"names": ["a", "b", 3]})
        # Non-matching element (3) dropped.
        self.assertEqual(props.get_scalar_list("names", str), ["a", "b"])

    def test_get_scalar_list_ints_drops_bool(self):
        props = ConfigProperties({"nums": [1, 2, True]})
        self.assertEqual(props.get_scalar_list("nums", int), [1, 2])

    def test_get_scalar_list_missing_returns_none(self):
        self.assertIsNone(ConfigProperties({}).get_scalar_list("x", str))


class TestNodeToMapping(unittest.TestCase):
    def test_dataclass_node_converted_recursively(self):
        node = ExperimentalInstrumentation(
            general=ExperimentalGeneralInstrumentation(
                stability_opt_in_list="http"
            )
        )
        mapping = _node_to_mapping(node)
        self.assertEqual(mapping["general"]["stability_opt_in_list"], "http")

    def test_none_yields_empty_mapping(self):
        self.assertEqual(_node_to_mapping(None), {})

    def test_config_properties_over_instrumentation_node(self):
        node = ExperimentalInstrumentation(
            general=ExperimentalGeneralInstrumentation(
                stability_opt_in_list="http"
            )
        )
        props = ConfigProperties(_node_to_mapping(node))
        general = props.get_config("general")
        self.assertIsInstance(general, ConfigProperties)
        self.assertEqual(general.get_string("stability_opt_in_list"), "http")


class TestGlobalConfigProvider(unittest.TestCase):
    def setUp(self):
        # Reset the module global before each test.
        config_provider_module._CONFIG_PROVIDER = None

    def test_get_returns_none_when_unset(self):
        self.assertIsNone(get_config_provider())

    def test_set_and_get(self):
        provider = ConfigProvider(ConfigProperties({"k": "v"}))
        set_config_provider(provider)
        self.assertIs(get_config_provider(), provider)
        self.assertEqual(
            get_config_provider().get_instrumentation_config().get_string("k"),
            "v",
        )
