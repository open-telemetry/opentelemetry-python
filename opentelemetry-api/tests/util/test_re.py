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

from opentelemetry.util.re import parse_env_headers


class TestParseHeaders(unittest.TestCase):
    @staticmethod
    def _common_test_cases():
        return [
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

    def test_parse_env_headers(self):
        inp = self._common_test_cases() + [
            # invalid header value
            ("key=value othervalue", [], True),
        ]
        for case_ in inp:
            headers, expected, warn = case_
            with self.subTest(headers=headers):
                if warn:
                    with self.assertLogs(level="WARNING") as cm:
                        self.assertEqual(
                            parse_env_headers(headers), dict(expected)
                        )
                        self.assertTrue(
                            "Header format invalid! Header values in environment "
                            "variables must be URL encoded per the OpenTelemetry "
                            "Protocol Exporter specification:"
                            in cm.records[0].message,
                        )
                else:
                    self.assertEqual(
                        parse_env_headers(headers), dict(expected)
                    )

    def test_parse_env_headers_liberal(self):
        inp = self._common_test_cases() + [
            # valid header value
            ("key=value othervalue", [("key", "value othervalue")], False),
            (
                "key=value Other_Value==",
                [("key", "value Other_Value==")],
                False,
            ),
        ]
        for case_ in inp:
            headers, expected, warn = case_
            with self.subTest(headers=headers):
                if warn:
                    with self.assertLogs(level="WARNING") as cm:
                        self.assertEqual(
                            parse_env_headers(headers, liberal=True),
                            dict(expected),
                        )
                        self.assertTrue(
                            "Header format invalid! Header values in environment "
                            "variables must be URL encoded per the OpenTelemetry "
                            "Protocol Exporter specification or a comma separated "
                            "list of name=value occurrences:"
                            in cm.records[0].message,
                        )
                else:
                    self.assertEqual(
                        parse_env_headers(headers, liberal=True),
                        dict(expected),
                    )
