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

        logger = create_logger(handler, "test_logger")

        logger.warning("test message")

        self.assertEqual(1, len(logger_provider._logger_cache))
        self.assertTrue(
            ("test_logger", "", None) in logger_provider._logger_cache
        )

        rounds = 100
        for _ in range(rounds):
            logger.warning("test message")

        self.assertEqual(1, len(logger_provider._logger_cache))
        self.assertTrue(
            ("test_logger", "", None) in logger_provider._logger_cache
        )

    def test_get_logger_multiple_loggers(self):
        handler, logger_provider = set_up_logging_handler(level=logging.DEBUG)

        num_loggers = 10
        loggers = [create_logger(handler, str(i)) for i in range(num_loggers)]

        for logger in loggers:
            logger.warning("test message")

        self.assertEqual(num_loggers, len(logger_provider._logger_cache))
        print(logger_provider._logger_cache)
        for logger in loggers:
            self.assertTrue(
                (logger.name, "", None) in logger_provider._logger_cache
            )

        rounds = 100
        for _ in range(rounds):
            for logger in loggers:
                logger.warning("test message")

        self.assertEqual(num_loggers, len(logger_provider._logger_cache))
        for logger in loggers:
            self.assertTrue(
                (logger.name, "", None) in logger_provider._logger_cache
            )
