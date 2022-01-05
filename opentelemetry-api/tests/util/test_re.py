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

# type: ignore

import unittest

from opentelemetry.util.re import parse_headers


class TestParseHeaders(unittest.TestCase):
    def test_parse_headers(self):
        inp = [
            # invalid header name
            ("=value", [], True),
            ("}key=value", [], True),
            ("@key()=value", [], True),
            ("/key=value", [], True),
            # invalid header value
            ("name=\\", [], True),
            ('name=value"', [], True),
            ("name=;value", [], True),
            # different header values
            ("name=", [("name", "")], False),
            ("name===value=", [("name", "==value=")], False),
            # url-encoded headers
            ("key=value%20with%20space", [("key", "value with space")], False),
            ("key%21=value", [("key!", "value")], False),
            ("%20key%20=%20value%20", [("key", "value")], False),
            # header name case normalization
            ("Key=Value", [("key", "Value")], False),
            # mix of valid and invalid headers
            (
                "name1=value1,invalidName, name2 =   value2   , name3=value3==",
                [
                    (
                        "name1",
                        "value1",
                    ),
                    ("name2", "value2"),
                    ("name3", "value3=="),
                ],
                True,
            ),
            (
                "=name=valu3; key1; key2, content  =  application, red=\tvelvet; cake",
                [("content", "application")],
                True,
            ),
        ]
        for case in inp:
            s, expected, warn = case
            if warn:
                with self.assertLogs(level="WARNING") as cm:
                    self.assertEqual(parse_headers(s), dict(expected))
                    self.assertTrue(
                        "Header doesn't match the format:"
                        in cm.records[0].message,
                    )
            else:
                self.assertEqual(parse_headers(s), dict(expected))
