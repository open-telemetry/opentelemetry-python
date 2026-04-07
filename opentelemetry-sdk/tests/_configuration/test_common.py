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

from opentelemetry.sdk._configuration._common import _parse_headers


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
