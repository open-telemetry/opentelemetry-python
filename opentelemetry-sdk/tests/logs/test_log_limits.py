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

from opentelemetry.sdk._logs import LogLimits
from opentelemetry.sdk._logs._internal import (
    _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
)


class TestLogLimits(unittest.TestCase):
    def test_log_limits_repr_unset(self):
        expected = f"LogLimits(max_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, max_attribute_length=None)"
        limits = str(LogLimits())

        self.assertEqual(expected, limits)

    def test_log_limits_max_attributes(self):
        expected = 1
        limits = LogLimits(max_attributes=1)

        self.assertEqual(expected, limits.max_attributes)

    def test_log_limits_max_attribute_length(self):
        expected = 1
        limits = LogLimits(max_attribute_length=1)

        self.assertEqual(expected, limits.max_attribute_length)
