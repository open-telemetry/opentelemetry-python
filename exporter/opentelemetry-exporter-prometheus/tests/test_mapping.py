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

from unittest import TestCase

from opentelemetry.exporter.prometheus._mapping import (
    map_unit,
    sanitize_attribute,
    sanitize_full_name,
)


class TestMapping(TestCase):
    def test_sanitize_full_name(self):
        self.assertEqual(
            sanitize_full_name("valid_metric_name"), "valid_metric_name"
        )
        self.assertEqual(
            sanitize_full_name("VALID_METRIC_NAME"), "VALID_METRIC_NAME"
        )
        self.assertEqual(
            sanitize_full_name("_valid_metric_name"), "_valid_metric_name"
        )
        self.assertEqual(
            sanitize_full_name("valid:metric_name"), "valid:metric_name"
        )
        self.assertEqual(
            sanitize_full_name("valid_1_metric_name"), "valid_1_metric_name"
        )
        self.assertEqual(
            sanitize_full_name("1leading_digit"), "_leading_digit"
        )
        self.assertEqual(
            sanitize_full_name("consective_____underscores"),
            "consective_underscores",
        )
        self.assertEqual(
            sanitize_full_name("1_~#consective_underscores"),
            "_consective_underscores",
        )
        self.assertEqual(
            sanitize_full_name("1!2@3#4$5%6^7&8*9(0)_-"),
            "_2_3_4_5_6_7_8_9_0_",
        )
        self.assertEqual(sanitize_full_name("foo,./?;:[]{}bar"), "foo_:_bar")
        self.assertEqual(sanitize_full_name("TestString"), "TestString")
        self.assertEqual(sanitize_full_name("aAbBcC_12_oi"), "aAbBcC_12_oi")

    def test_sanitize_attribute(self):
        self.assertEqual(
            sanitize_attribute("valid_attr_key"), "valid_attr_key"
        )
        self.assertEqual(
            sanitize_attribute("VALID_attr_key"), "VALID_attr_key"
        )
        self.assertEqual(
            sanitize_attribute("_valid_attr_key"), "_valid_attr_key"
        )
        self.assertEqual(
            sanitize_attribute("valid_1_attr_key"), "valid_1_attr_key"
        )
        self.assertEqual(
            sanitize_attribute("sanitize:colons"), "sanitize_colons"
        )
        self.assertEqual(
            sanitize_attribute("1leading_digit"), "_leading_digit"
        )
        self.assertEqual(
            sanitize_attribute("1_~#consective_underscores"),
            "_consective_underscores",
        )
        self.assertEqual(
            sanitize_attribute("1!2@3#4$5%6^7&8*9(0)_-"),
            "_2_3_4_5_6_7_8_9_0_",
        )
        self.assertEqual(sanitize_attribute("foo,./?;:[]{}bar"), "foo_bar")
        self.assertEqual(sanitize_attribute("TestString"), "TestString")
        self.assertEqual(sanitize_attribute("aAbBcC_12_oi"), "aAbBcC_12_oi")

    def test_map_unit(self):
        # select hardcoded mappings
        self.assertEqual(map_unit("s"), "seconds")
        self.assertEqual(map_unit("By"), "bytes")
        self.assertEqual(map_unit("m"), "meters")
        # should work with UCUM annotations as well
        self.assertEqual(map_unit("g{dogfood}"), "grams")

        # UCUM "default unit" aka unity and equivalent UCUM annotations should be stripped
        self.assertEqual(map_unit("1"), "")
        self.assertEqual(map_unit("{}"), "")
        self.assertEqual(map_unit("{request}"), "")
        self.assertEqual(map_unit("{{{;@#$}}}"), "")
        self.assertEqual(map_unit("{unit with space}"), "")

        # conversion of per units
        self.assertEqual(map_unit("km/h"), "km_per_hour")
        self.assertEqual(map_unit("m/s"), "meters_per_second")
        self.assertEqual(map_unit("{foo}/s"), "per_second")
        self.assertEqual(map_unit("foo/bar"), "foo_per_bar")
        self.assertEqual(map_unit("2fer/store"), "2fer_per_store")

        # should be sanitized to become part of the metric name without surrounding "_"
        self.assertEqual(map_unit("____"), "")
        self.assertEqual(map_unit("____"), "")
        self.assertEqual(map_unit("1:foo#@!"), "1:foo")
        # should not be interpreted as a per unit since there is no denominator
        self.assertEqual(map_unit("m/"), "m")
        self.assertEqual(map_unit("m/{bar}"), "m")
