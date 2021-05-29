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

from opentelemetry.sdk.logs.severity import (
    SeverityNumber,
    std_to_opentelemetry,
)


class TestSeverityNumber(unittest.TestCase):
    def test_python_log_level_to_otel_conversion(self):
        self.assertEqual(std_to_opentelemetry(6), SeverityNumber.UNSPECIFIED)
        self.assertEqual(std_to_opentelemetry(10), SeverityNumber.DEBUG)
        self.assertEqual(std_to_opentelemetry(11), SeverityNumber.DEBUG2)
        self.assertEqual(std_to_opentelemetry(13), SeverityNumber.DEBUG4)
        self.assertEqual(std_to_opentelemetry(17), SeverityNumber.DEBUG4)
        self.assertEqual(std_to_opentelemetry(100), SeverityNumber.FATAL4)
        self.assertEqual(std_to_opentelemetry(53), SeverityNumber.FATAL4)
        self.assertEqual(std_to_opentelemetry(30), SeverityNumber.WARN)
        self.assertEqual(std_to_opentelemetry(40), SeverityNumber.ERROR)
        self.assertEqual(std_to_opentelemetry(50), SeverityNumber.FATAL)
        self.assertEqual(std_to_opentelemetry(26), SeverityNumber.INFO4)
        self.assertEqual(std_to_opentelemetry(32), SeverityNumber.WARN3)
