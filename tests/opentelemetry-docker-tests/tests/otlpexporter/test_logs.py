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

from __future__ import annotations

import time
import unittest

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from . import LOG_EXPORTERS


def _setup(factory):
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(factory()))
    logger = provider.get_logger(
        "test.logger", version="0.1.0", schema_url="https://example.com"
    )
    return provider, logger


class TestLogExport(unittest.TestCase):
    def test_basic_log(self):
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, logger = _setup(factory)

                logger.emit(
                    LogRecord(
                        body="hello world",
                        severity_number=SeverityNumber.INFO,
                    )
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_severity_levels(self):
        """Emit one log per severity family."""
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, logger = _setup(factory)

                for sev in (
                    SeverityNumber.TRACE,
                    SeverityNumber.DEBUG,
                    SeverityNumber.INFO,
                    SeverityNumber.WARN,
                    SeverityNumber.ERROR,
                    SeverityNumber.FATAL,
                ):
                    logger.emit(
                        LogRecord(
                            body=f"log at {sev.name}",
                            severity_number=sev,
                            severity_text=sev.name,
                        )
                    )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_log_with_attributes(self):
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, logger = _setup(factory)

                logger.emit(
                    LogRecord(
                        body="structured log",
                        severity_number=SeverityNumber.INFO,
                        attributes={
                            "str_attr": "value",
                            "int_attr": 42,
                            "float_attr": 3.14,
                            "bool_attr": True,
                            "list_attr": [1, 2, 3],
                        },
                    )
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_log_with_timestamp(self):
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, logger = _setup(factory)

                now = time.time_ns()
                logger.emit(
                    LogRecord(
                        body="timed log",
                        severity_number=SeverityNumber.DEBUG,
                        timestamp=now,
                        observed_timestamp=now,
                    )
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_log_body_types(self):
        """Body can be a string, int, float, bool, or list."""
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, logger = _setup(factory)

                for body in ("text", 42, 3.14, True, [1, "two", 3.0]):
                    logger.emit(
                        LogRecord(
                            body=body,
                            severity_number=SeverityNumber.INFO,
                        )
                    )

                self.assertTrue(provider.force_flush())
                provider.shutdown()

    def test_resource_attributes(self):
        for protocol, factory in LOG_EXPORTERS:
            with self.subTest(protocol=protocol):
                resource = Resource.create(
                    {"service.name": "test-svc", "service.version": "1.0.0"}
                )
                provider = LoggerProvider(resource=resource)
                provider.add_log_record_processor(
                    SimpleLogRecordProcessor(factory())
                )
                logger = provider.get_logger("test.logger")

                logger.emit(
                    LogRecord(
                        body="log with resource",
                        severity_number=SeverityNumber.INFO,
                    )
                )

                self.assertTrue(provider.force_flush())
                provider.shutdown()
