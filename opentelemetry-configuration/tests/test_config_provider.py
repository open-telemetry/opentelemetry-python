# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch

import opentelemetry.configuration._config_provider as config_provider_module
from opentelemetry.configuration._config_provider import (
    ConfigProperties,
    ConfigProvider,
    NoOpConfigProvider,
    ProxyConfigProvider,
    _node_to_mapping,
    get_config_provider,
    set_config_provider,
)
from opentelemetry.configuration.models import (
    ExperimentalGeneralInstrumentation,
    ExperimentalInstrumentation,
)
from opentelemetry.util._once import Once


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
            self.props.keys(),
            {"name", "flag", "count", "ratio", "whole"},
        )

    def test_keys_returns_set(self):
        self.assertIsInstance(self.props.keys(), set)

    def test_contains(self):
        self.assertIn("name", self.props)
        self.assertNotIn("nope", self.props)

    def test_present_null_distinguishable_from_absent(self):
        props = ConfigProperties({"endpoint": None})
        # Both getters return None, so the caller uses membership or keys() to
        # tell "present with a null value" from "not set".
        self.assertIsNone(props.get_string("endpoint"))
        self.assertIsNone(props.get_string("absent"))
        self.assertIn("endpoint", props)
        self.assertNotIn("absent", props)
        self.assertEqual(props.keys(), {"endpoint"})


class TestConfigPropertiesTypeMismatch(unittest.TestCase):
    @patch("opentelemetry.configuration._config_provider._logger")
    def test_present_wrong_type_logs_warning(self, mock_logger):
        props = ConfigProperties({"count": "not-a-number"})
        self.assertIsNone(props.get_int("count"))
        mock_logger.warning.assert_called_once()

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_missing_key_does_not_log(self, mock_logger):
        props = ConfigProperties({})
        self.assertIsNone(props.get_int("count"))
        mock_logger.warning.assert_not_called()

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_get_int_rejecting_bool_logs(self, mock_logger):
        props = ConfigProperties({"count": True})
        self.assertIsNone(props.get_int("count"))
        mock_logger.warning.assert_called_once()


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

    def test_get_config_list_accepts_empty_mapping_element(self):
        props = ConfigProperties({"servers": [{}, {"host": "a"}]})
        result = props.get_config_list("servers")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].keys(), set())
        self.assertEqual(result[1].get_string("host"), "a")

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_get_config_list_null_element_logs_and_returns_none(self, mock_logger):
        props = ConfigProperties({"servers": [{"host": "a"}, None]})
        self.assertIsNone(props.get_config_list("servers"))
        mock_logger.warning.assert_called_once()
        # The warning names the offending element, not the whole list.
        self.assertIn("servers[1]", mock_logger.warning.call_args.args)

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_get_config_list_scalar_element_logs_and_returns_none(self, mock_logger):
        props = ConfigProperties({"servers": [5]})
        self.assertIsNone(props.get_config_list("servers"))
        mock_logger.warning.assert_called_once()
        self.assertIn("servers[0]", mock_logger.warning.call_args.args)

    def test_get_string_list_drops_non_matching(self):
        props = ConfigProperties({"names": ["a", "b", 3]})
        # Non-matching element (3) dropped.
        self.assertEqual(props.get_string_list("names"), ["a", "b"])

    def test_get_int_list_drops_bool(self):
        props = ConfigProperties({"nums": [1, 2, True]})
        self.assertEqual(props.get_int_list("nums"), [1, 2])

    def test_get_float_list_widens_int(self):
        props = ConfigProperties({"nums": [1, 2.5]})
        self.assertEqual(props.get_float_list("nums"), [1.0, 2.5])

    def test_get_bool_list(self):
        props = ConfigProperties({"flags": [True, False, "x"]})
        self.assertEqual(props.get_bool_list("flags"), [True, False])

    def test_get_string_list_missing_returns_none(self):
        self.assertIsNone(ConfigProperties({}).get_string_list("x"))

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_get_string_list_non_sequence_logs_and_returns_none(self, mock_logger):
        props = ConfigProperties({"names": "not-a-list"})
        self.assertIsNone(props.get_string_list("names"))
        mock_logger.warning.assert_called_once()


class TestNodeToMapping(unittest.TestCase):
    def test_dataclass_node_converted_recursively(self):
        node = ExperimentalInstrumentation(general=ExperimentalGeneralInstrumentation(stability_opt_in_list="http"))
        mapping = _node_to_mapping(node)
        self.assertEqual(mapping["general"]["stability_opt_in_list"], "http")

    def test_none_yields_empty_mapping(self):
        self.assertEqual(_node_to_mapping(None), {})

    def test_config_properties_over_instrumentation_node(self):
        node = ExperimentalInstrumentation(general=ExperimentalGeneralInstrumentation(stability_opt_in_list="http"))
        props = ConfigProperties(_node_to_mapping(node))
        general = props.get_config("general")
        self.assertIsInstance(general, ConfigProperties)
        self.assertEqual(general.get_string("stability_opt_in_list"), "http")


class TestGlobalConfigProvider(unittest.TestCase):
    def setUp(self):
        # Reset the module global and its set-once guard before each test.
        # pylint: disable=protected-access
        config_provider_module._CONFIG_PROVIDER = None
        config_provider_module._CONFIG_PROVIDER_SET_ONCE = Once()

    def test_get_returns_proxy_when_unset(self):
        provider = get_config_provider()
        self.assertIsInstance(provider, ProxyConfigProvider)
        # The proxy exposes empty instrumentation config until one is set, so
        # callers can traverse it without None checks.
        self.assertEqual(
            provider.get_instrumentation_config().keys(),
            set(),
        )
        self.assertIsNone(provider.get_instrumentation_config().get_string("anything"))

    def test_proxy_forwards_to_later_set_provider(self):
        # A caller that grabs the provider before it is set still sees the
        # config installed later, mirroring ProxyTracerProvider.
        proxy = get_config_provider()
        self.assertIsInstance(proxy, ProxyConfigProvider)
        set_config_provider(ConfigProvider(ConfigProperties({"k": "v"})))
        self.assertEqual(proxy.get_instrumentation_config().get_string("k"), "v")

    def test_noop_provider_is_empty(self):
        provider = NoOpConfigProvider()
        self.assertEqual(provider.get_instrumentation_config().keys(), set())

    def test_set_and_get(self):
        provider = ConfigProvider(ConfigProperties({"k": "v"}))
        set_config_provider(provider)
        self.assertIs(get_config_provider(), provider)
        self.assertEqual(
            get_config_provider().get_instrumentation_config().get_string("k"),
            "v",
        )

    @patch("opentelemetry.configuration._config_provider._logger")
    def test_set_is_once_only(self, mock_logger):
        first = ConfigProvider(ConfigProperties({"k": "first"}))
        second = ConfigProvider(ConfigProperties({"k": "second"}))
        set_config_provider(first)
        set_config_provider(second)
        # The second set is ignored and a warning is logged, matching
        # set_tracer_provider semantics.
        self.assertIs(get_config_provider(), first)
        mock_logger.warning.assert_called_once_with("Overriding of current ConfigProvider is not allowed")
