import logging

import pytest

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)


def _set_up_logging_handler(level):
    logger_provider = LoggerProvider()
    exporter = InMemoryLogExporter()
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
