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

from opentelemetry.propagators.textmap import DefaultGetter


class TestDefaultGetter(unittest.TestCase):
    def test_get_none(self):
        getter = DefaultGetter()
        carrier = {}
        val = getter.get(carrier, "test")
        self.assertIsNone(val)

    def test_get_str(self):
        getter = DefaultGetter()
        carrier = {"test": "val"}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_get_iter(self):
        getter = DefaultGetter()
        carrier = {"test": ["val"]}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_keys(self):
        getter = DefaultGetter()
        keys = getter.keys({"test": "val"})
        self.assertEqual(keys, ["test"])
