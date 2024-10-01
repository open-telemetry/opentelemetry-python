import logging

import pytest

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)


def set_up_logging_handler(level):
    logger_provider = LoggerProvider()
    exporter = InMemoryLogExporter()
    processor = SimpleLogRecordProcessor(exporter=exporter)
    logger_provider.add_log_record_processor(processor)
    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    return handler


def create_logger(handler, name):
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


@pytest.mark.parametrize("num_loggers", [1, 10, 100, 1000, 10000])
def test_simple_get_logger_different_names(benchmark, num_loggers):
    handler = set_up_logging_handler(level=logging.DEBUG)
    loggers = [
        create_logger(handler, str(f"logger_{i}")) for i in range(num_loggers)
    ]

    def benchmark_get_logger():
        for i in range(10000):
            loggers[i % num_loggers].warning("test message")

    benchmark(benchmark_get_logger)
