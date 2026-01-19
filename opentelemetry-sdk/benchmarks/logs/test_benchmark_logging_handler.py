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

import pytest

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)


def _set_up_logging_handler(level):
    logger_provider = LoggerProvider()
    exporter = InMemoryLogRecordExporter()
    processor = SimpleLogRecordProcessor(exporter=exporter)
    logger_provider.add_log_record_processor(processor)
    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    return handler


def _create_logger(handler, name):
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


@pytest.mark.parametrize("num_loggers", [1, 10, 100, 1000])
def test_simple_get_logger_different_names(benchmark, num_loggers):
    handler = _set_up_logging_handler(level=logging.DEBUG)
    loggers = [
        _create_logger(handler, str(f"logger_{i}")) for i in range(num_loggers)
    ]

    def benchmark_get_logger():
        for index in range(1000):
            loggers[index % num_loggers].warning("test message")

    benchmark(benchmark_get_logger)
