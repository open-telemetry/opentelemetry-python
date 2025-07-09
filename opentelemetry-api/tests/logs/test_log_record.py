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
from unittest.mock import patch

from opentelemetry._logs import LogRecord

OBSERVED_TIMESTAMP = "OBSERVED_TIMESTAMP"


class TestLogRecord(unittest.TestCase):
    @patch("opentelemetry._logs._internal.time_ns")
    def test_log_record_observed_timestamp_default(self, time_ns_mock):  # type: ignore
        time_ns_mock.return_value = OBSERVED_TIMESTAMP
        self.assertEqual(LogRecord().observed_timestamp, OBSERVED_TIMESTAMP)
