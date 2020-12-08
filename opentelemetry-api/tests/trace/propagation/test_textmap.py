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

from opentelemetry.trace.propagation.textmap import DictGetter


class TestDictGetter(unittest.TestCase):
    def test_get_none(self):
        getter = DictGetter()
        carrier = {}
        val = getter.get(carrier, "test")
        self.assertIsNone(val)

    def test_get_str(self):
        getter = DictGetter()
        carrier = {"test": "val"}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_get_iter(self):
        getter = DictGetter()
        carrier = {"test": ["val"]}
        val = getter.get(carrier, "test")
        self.assertEqual(val, ["val"])

    def test_keys(self):
        getter = DictGetter()
        keys = getter.keys({"test": "val"})
        self.assertEqual(keys, ["test"])
