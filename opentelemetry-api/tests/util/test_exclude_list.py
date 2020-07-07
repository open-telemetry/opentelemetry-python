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
from unittest import mock

from opentelemetry.util import ExcludeList


class TestExcludeList(unittest.TestCase):
    def test_basic(self):
        regexes = ExcludeList(["path/123", "http://site.com/other_path"])
        self.assertTrue(regexes.url_disabled("http://site.com/path/123"))
        self.assertTrue(regexes.url_disabled("http://site.com/path/123/abc"))
        self.assertTrue(
            regexes.url_disabled("https://site.com/path/123?arg=other")
        )

        self.assertFalse(regexes.url_disabled("https://site.com/path/abc/123"))
        self.assertFalse(regexes.url_disabled("https://site.com/path"))

        self.assertTrue(regexes.url_disabled("http://site.com/other_path"))
        self.assertTrue(regexes.url_disabled("http://site.com/other_path?abc"))

        self.assertFalse(regexes.url_disabled("https://site.com/other_path"))
        self.assertFalse(
            regexes.url_disabled("https://site.com/abc/other_path")
        )

    def test_regex(self):
        regexes = ExcludeList(
            [r"^https?://site\.com/path/123$", r"^http://.*\?arg=foo"]
        )

        self.assertTrue(regexes.url_disabled("http://site.com/path/123"))
        self.assertTrue(regexes.url_disabled("https://site.com/path/123"))

        self.assertFalse(regexes.url_disabled("http://site.com/path/123/abc"))
        self.assertFalse(regexes.url_disabled("http://site,com/path/123"))

        self.assertTrue(
            regexes.url_disabled("http://site.com/path/123?arg=foo")
        )
        self.assertTrue(
            regexes.url_disabled("http://site.com/path/123?arg=foo,arg2=foo2")
        )

        self.assertFalse(
            regexes.url_disabled("https://site.com/path/123?arg=foo")
        )
