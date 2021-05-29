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

import logging
import unittest
from unittest.mock import Mock

from opentelemetry.sdk.logs import LogEmitterProvider, LogProcessor


class AnotherLogProcessor(LogProcessor):
    def __init__(self, exporter, logs_list):
        self._exporter = exporter
        self._log_list = logs_list
        self._closed = False

    def emit(self, log_data):
        if self._closed:
            return
        self._log_list.append(
            (log_data.log_record.body, log_data.log_record.severity_text)
        )

    def shutdown(self):
        self._closed = True
        self._exporter.shutdown()

    def force_flush(self, timeout_millis=30000):
        self._log_list.clear()
        return True


class TestLogProcessor(unittest.TestCase):
    def test_log_processor(self):
        provider = LogEmitterProvider()
        log_emitter = provider.get_log_emitter(__name__)

        logs_list_1 = []
        processor1 = AnotherLogProcessor(Mock(), logs_list_1)
        logs_list_2 = []
        processor2 = AnotherLogProcessor(Mock(), logs_list_2)

        logger = logging.getLogger("test.span.processor")
        logger.addHandler(log_emitter)

        # Test no proessor added
        logger.critical("Odisha, we have another major cyclone")

        self.assertEqual(len(logs_list_1), 0)
        self.assertEqual(len(logs_list_2), 0)

        # Add one processor
        provider.add_log_processor(processor1)
        logger.warning("Brace yourself")
        logger.error("Some error message")

        expected_list_1 = [
            ("Brace yourself", "WARNING"),
            ("Some error message", "ERROR"),
        ]
        self.assertEqual(logs_list_1, expected_list_1)

        # Add another processor
        provider.add_log_processor(processor2)
        logger.critical("Something disastrous")
        expected_list_1.append(("Something disastrous", "CRITICAL"))

        expected_list_2 = [("Something disastrous", "CRITICAL")]

        self.assertEqual(logs_list_1, expected_list_1)
        self.assertEqual(logs_list_2, expected_list_2)
