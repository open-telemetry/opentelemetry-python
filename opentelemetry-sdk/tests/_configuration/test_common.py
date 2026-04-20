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

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._common import (
    _parse_headers,
    load_entry_point,
)
from opentelemetry.sdk._configuration._exceptions import ConfigurationError


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
