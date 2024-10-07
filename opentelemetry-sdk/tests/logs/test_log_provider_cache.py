import logging
import unittest

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
    return handler, logger_provider


def create_logger(handler, name):
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


class TestLogProviderCache(unittest.TestCase):

    def test_get_logger_single_handler(self):
        handler, logger_provider = set_up_logging_handler(level=logging.DEBUG)

        cache_info = logger_provider._get_logger_cached.cache_clear()

        logger = create_logger(handler, "test_logger")

        # Ensure logger is lazily cached
        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(0, cache_info.currsize)

        logger.warning("test message")

        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(1, cache_info.currsize)
        self.assertEqual(1, cache_info.misses)

        # Ensure only one logger is cached
        rounds = 100
        for _ in range(rounds):
            logger.warning("test message")

        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(1, cache_info.currsize)
        self.assertEqual(1, cache_info.misses)

    def test_get_logger_multiple_loggers(self):
        handler, logger_provider = set_up_logging_handler(level=logging.DEBUG)

        cache_info = logger_provider._get_logger_cached.cache_clear()

        num_loggers = 10
        loggers = [create_logger(handler, str(i)) for i in range(num_loggers)]

        # Ensure loggers are lazily cached
        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(0, cache_info.currsize)

        for logger in loggers:
            logger.warning("test message")

        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(num_loggers, cache_info.currsize)
        self.assertEqual(num_loggers, cache_info.misses)

        rounds = 100
        for _ in range(rounds):
            for logger in loggers:
                logger.warning("test message")

        cache_info = logger_provider._get_logger_cached.cache_info()
        self.assertEqual(num_loggers, cache_info.currsize)
        self.assertEqual(num_loggers, cache_info.misses)
