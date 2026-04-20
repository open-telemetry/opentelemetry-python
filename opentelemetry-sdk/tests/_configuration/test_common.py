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

import inspect
import unittest
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._common import (
    _additional_properties_support,
    _parse_headers,
    load_entry_point,
)
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    ExperimentalResourceDetector,
    LogRecordExporter,
    PushMetricExporter,
    Sampler,
    SpanExporter,
    TextMapPropagator,
)


class TestParseHeaders(unittest.TestCase):
    def test_both_none_returns_none(self):
        self.assertIsNone(_parse_headers(None, None))

    def test_empty_headers_list_returns_empty_dict(self):
        self.assertEqual(_parse_headers(None, ""), {})

    def test_headers_list_single_pair(self):
        self.assertEqual(
            _parse_headers(None, "x-api-key=secret"),
            {"x-api-key": "secret"},
        )

    def test_headers_list_multiple_pairs(self):
        self.assertEqual(
            _parse_headers(None, "x-api-key=secret,env=prod"),
            {"x-api-key": "secret", "env": "prod"},
        )

    def test_headers_list_strips_whitespace(self):
        self.assertEqual(
            _parse_headers(None, " x-api-key = secret , env = prod "),
            {"x-api-key": "secret", "env": "prod"},
        )

    def test_headers_list_value_with_equals(self):
        # value contains '=' — only split on the first one
        self.assertEqual(
            _parse_headers(None, "auth=Bearer tok=en"),
            {"auth": "Bearer tok=en"},
        )

    def test_headers_list_invalid_pair_ignored(self):
        # malformed entry (no '=') should be skipped with a warning
        result = _parse_headers(None, "bad,x-key=val")
        self.assertEqual(result, {"x-key": "val"})

    def test_struct_headers_only(self):
        headers = [
            SimpleNamespace(name="x-api-key", value="secret"),
            SimpleNamespace(name="env", value="prod"),
        ]
        self.assertEqual(
            _parse_headers(headers, None),
            {"x-api-key": "secret", "env": "prod"},
        )

    def test_struct_header_none_value_becomes_empty_string(self):
        headers = [SimpleNamespace(name="x-key", value=None)]
        self.assertEqual(_parse_headers(headers, None), {"x-key": ""})

    def test_struct_headers_override_headers_list(self):
        # struct takes priority over headers_list for same key
        headers = [SimpleNamespace(name="x-api-key", value="from-struct")]
        self.assertEqual(
            _parse_headers(headers, "x-api-key=from-list,env=prod"),
            {"x-api-key": "from-struct", "env": "prod"},
        )

    def test_both_empty_struct_and_none_list_returns_empty_dict(self):
        self.assertEqual(_parse_headers([], None), {})


class TestLoadEntryPoint(unittest.TestCase):
    def test_returns_loaded_class(self):
        mock_class = MagicMock()
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_class
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            result = load_entry_point("some_group", "some_name")
        self.assertIs(result, mock_class)

    def test_raises_when_not_found(self):
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                load_entry_point("some_group", "missing")
        self.assertIn("missing", str(ctx.exception))
        self.assertIn("some_group", str(ctx.exception))

    def test_wraps_load_exception_in_configuration_error(self):
        mock_ep = MagicMock()
        mock_ep.load.side_effect = ImportError("bad import")
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                load_entry_point("some_group", "some_name")
        self.assertIn("bad import", str(ctx.exception))

    def test_instantiation_error_not_wrapped(self):
        """load_entry_point returns the class; instantiation is the caller's
        responsibility. Errors from calling the returned class are NOT wrapped
        in ConfigurationError — they propagate as-is."""
        mock_class = MagicMock(side_effect=TypeError("bad init"))
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_class
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            cls = load_entry_point("some_group", "some_name")
            # load_entry_point itself succeeds
            self.assertIs(cls, mock_class)
            # Calling the returned class raises the original error, not
            # ConfigurationError
            with self.assertRaises(TypeError, msg="bad init"):
                cls()


class TestAdditionalPropertiesSupport(unittest.TestCase):
    def setUp(self):
        @_additional_properties_support
        @dataclass
        class _SampleConfig:
            known_field: dict | None = None
            another_field: str | None = None
            additional_properties: dict = field(default_factory=dict)

        self.cls = _SampleConfig

    def test_known_fields_work_normally(self):
        obj = self.cls(known_field={}, another_field="val")
        self.assertEqual(obj.known_field, {})
        self.assertEqual(obj.another_field, "val")
        self.assertEqual(obj.additional_properties, {})

    def test_unknown_kwargs_captured_in_additional_properties(self):
        # pylint: disable=unexpected-keyword-arg
        obj = self.cls(my_plugin={"key": "val"})
        self.assertIsNone(obj.known_field)
        self.assertEqual(
            obj.additional_properties, {"my_plugin": {"key": "val"}}
        )

    def test_mixed_known_and_unknown_kwargs(self):
        # pylint: disable=unexpected-keyword-arg
        obj = self.cls(known_field={}, my_plugin={})
        self.assertEqual(obj.known_field, {})
        self.assertEqual(obj.additional_properties, {"my_plugin": {}})

    def test_no_args_creates_empty_additional_properties(self):
        obj = self.cls()
        self.assertIsNone(obj.known_field)
        self.assertEqual(obj.additional_properties, {})

    def test_signature_preserves_known_fields_and_adds_kwargs(self):
        sig = inspect.signature(self.cls)
        param_names = list(sig.parameters.keys())
        self.assertIn("known_field", param_names)
        self.assertIn("another_field", param_names)
        # **kwargs signals that extras are accepted
        kwargs_param = sig.parameters.get("kwargs")
        self.assertIsNotNone(kwargs_param)
        self.assertEqual(kwargs_param.kind, inspect.Parameter.VAR_KEYWORD)


class TestGeneratedModelsHaveAdditionalProperties(unittest.TestCase):
    """Guards against regressions in the custom datamodel-codegen template.

    The codegen/dataclass.jinja2 template conditionally applies the
    @_additional_properties_support decorator based on the
    additionalPropertiesType template variable. If datamodel-codegen
    changes how it passes this variable, these tests will fail.
    """

    def _assert_supports_additional_properties(self, model_cls):
        # pylint: disable=unexpected-keyword-arg
        obj = model_cls(_test_plugin_key={})
        self.assertTrue(
            hasattr(obj, "additional_properties"),
            f"{model_cls.__name__} missing additional_properties field",
        )
        self.assertIn("_test_plugin_key", obj.additional_properties)

    def test_sampler(self):
        self._assert_supports_additional_properties(Sampler)

    def test_span_exporter(self):
        self._assert_supports_additional_properties(SpanExporter)

    def test_text_map_propagator(self):
        self._assert_supports_additional_properties(TextMapPropagator)

    def test_resource_detector(self):
        self._assert_supports_additional_properties(
            ExperimentalResourceDetector
        )

    def test_log_record_exporter(self):
        self._assert_supports_additional_properties(LogRecordExporter)

    def test_push_metric_exporter(self):
        self._assert_supports_additional_properties(PushMetricExporter)
